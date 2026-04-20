"""CodePipeline stack — one pipeline per environment.

Dev pipeline:  watches `dev` branch, auto-deploys on push.
Prod pipeline: watches `main` branch, auto-deploys on PR merge from dev.
"""

import json
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import pipelines, aws_codebuild as codebuild, aws_secretsmanager as secretsmanager
from stacks.demo_stack import DemoStack


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

        # Store pipeline config in Secrets Manager so the synth step can read it
        config_secret_name = f"{project_name}-{stage_name.lower()}-pipeline-config"
        secret = secretsmanager.Secret(
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

        synth = pipelines.CodeBuildStep(
            "Synth",
            input=source,
            install_commands=["npm install -g aws-cdk"],
            commands=[
                "cd backend && pip install -r requirements.txt && pytest --timeout=30 -v",
                "cd ../frontend && npm ci && npm run test -- --run && npm run build",
                "cd ../infra && pip install -r requirements.txt && cdk synth",
            ],
            primary_output_directory="infra/cdk.out",
            build_environment=codebuild.BuildEnvironment(
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
            pipeline_name=f"{project_name}-{stage_name.lower()}",
            synth=synth,
        )

        stage = DemoStage(self, stage_name, project_name=project_name, stage_name=stage_name, env=kwargs.get("env"))

        deploy_frontend = pipelines.ShellStep(
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
        )

        pipeline.add_stage(stage, post=[deploy_frontend])


class DemoStage(cdk.Stage):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        stack = DemoStack(self, "DemoStack", project_name=project_name, stage_name=stage_name)

        self.bucket_name_output = stack.bucket_name_output
        self.distribution_id_output = stack.distribution_id_output
