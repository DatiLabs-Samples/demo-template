"""CodePipeline stack — one pipeline per environment.

Dev pipeline:  watches `dev` branch, auto-deploys on push.
Prod pipeline: watches `main` branch, auto-deploys on PR merge from dev.
"""

import json
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import pipelines, aws_codebuild as codebuild, aws_secretsmanager as secretsmanager, aws_iam as iam
from stacks.app_stack import AppStack


class PipelineStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        repo: str,
        branch: str,
        stage_name: str,
        connection_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        prefix = f"{project_name}-{stage_name.lower()}"

        # Store pipeline config in Secrets Manager so the synth step can read it
        config_secret_name = f"{prefix}-pipeline-config"
        secretsmanager.Secret(
            self, "PipelineConfig",
            secret_name=config_secret_name,
            secret_string_value=cdk.SecretValue.unsafe_plain_text(
                json.dumps({
                    "PROJECT_NAME": project_name,
                    "GITHUB_REPO": repo,
                    "CONNECTION_ARN": connection_arn,
                })
            ),
        )

        source = pipelines.CodePipelineSource.connection(
            repo, branch, connection_arn=connection_arn,
        )

        # Synth: pre-build the deps layer (cached pip), run backend tests,
        # build the frontend (cached npm), then `cdk synth`. The deps layer
        # is asset-hashed by content, so unchanged requirements.txt skips the
        # S3 upload during deploy.
        synth = pipelines.CodeBuildStep(
            "Synth",
            input=source,
            install_commands=["npm install -g aws-cdk"],
            commands=[
                # 1. Pre-build backend deps layer for ARM64 (Lambda runtime).
                #    pip cache (configured below) makes this near-instant on
                #    repeat builds. No --no-cache-dir.
                "mkdir -p backend/.layer/python",
                "pip install -r backend/requirements.txt -t backend/.layer/python "
                "--platform manylinux2014_aarch64 --only-binary=:all: "
                "--python-version 3.12 --implementation cp",
                # Strip bytecode caches so the layer asset hash stays stable
                # when deps haven't changed.
                "find backend/.layer -type d -name __pycache__ -prune -exec rm -rf {} + || true",

                # 2. Backend tests (reuses the warm pip cache).
                "cd backend && pip install -r requirements.txt && pytest --timeout=30 -v && cd ..",

                # 3. Frontend test + build (npm cache makes `npm ci` fast).
                "cd frontend && npm ci --prefer-offline --no-audit && npm run test -- --run && npm run build && cd ..",

                # 4. CDK synth.
                "cd infra && pip install -r requirements.txt && cdk synth",
            ],
            primary_output_directory="infra/cdk.out",
            partial_build_spec=codebuild.BuildSpec.from_object({
                "cache": {
                    "paths": [
                        "/root/.cache/pip/**/*",
                        "/root/.npm/**/*",
                    ],
                },
            }),
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2_STANDARD_3_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                environment_variables={
                    "PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                        type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                        value=f"{config_secret_name}:PROJECT_NAME",
                    ),
                    "GITHUB_REPO": codebuild.BuildEnvironmentVariable(
                        type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                        value=f"{config_secret_name}:GITHUB_REPO",
                    ),
                    "CONNECTION_ARN": codebuild.BuildEnvironmentVariable(
                        type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                        value=f"{config_secret_name}:CONNECTION_ARN",
                    ),
                }
            ),

        )

        pipeline = pipelines.CodePipeline(
            self, "Pipeline",
            pipeline_name=prefix,
            synth=synth,
            code_build_defaults=pipelines.CodeBuildOptions(
                cache=codebuild.Cache.bucket(
                    cdk.aws_s3.Bucket(self, "CacheBucket",
                        removal_policy=cdk.RemovalPolicy.DESTROY,
                        auto_delete_objects=True,
                        lifecycle_rules=[cdk.aws_s3.LifecycleRule(expiration=cdk.Duration.days(7))],
                    ),
                ),
            ),
        )

        stage = DemoStage(
            self, stage_name,
            project_name=project_name,
            stage_name=stage_name,
            env=kwargs.get("env"),
        )

        deploy_frontend = pipelines.CodeBuildStep(
            "DeployFrontend",
            input=synth.add_output_directory("frontend/dist"),
            env_from_cfn_outputs={
                "BUCKET_NAME": stage.bucket_name_output,
                "DISTRIBUTION_ID": stage.distribution_id_output,
            },
            commands=[
                "aws s3 sync . s3://$BUCKET_NAME --delete",
                'aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"',
            ],
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketLocation"],
                    resources=["arn:aws:s3:::*"],
                ),
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:DeleteObject"],
                    resources=["arn:aws:s3:::*/*"],
                ),
                iam.PolicyStatement(
                    actions=["cloudfront:CreateInvalidation"],
                    resources=["*"],
                ),
            ],
        )

        pipeline.add_stage(stage, post=[deploy_frontend])


class DemoStage(cdk.Stage):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        stack = AppStack(
            self, "AppStack",
            project_name=project_name,
            stage_name=stage_name,
            stack_name=f"{project_name}-{stage_name.lower()}-app",
        )

        self.bucket_name_output = stack.bucket_name_output
        self.distribution_id_output = stack.distribution_id_output
