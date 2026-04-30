"""Single-CodeBuild deploy stack — Source → Build (everything in one).

Replaces the previous CDK Pipelines architecture. One CodePipeline with two
stages: Source (GitHub via CodeConnection) and Build (one CodeBuild action
that runs tests, frontend build, `cdk deploy`, and frontend sync). Demos
don't need the multi-stage Synth/SelfMutate/FileAsset/Prepare/Deploy split,
and dropping it removes ~2 minutes of per-action CodeBuild overhead.
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    aws_s3 as s3,
)


class DeployStack(cdk.Stack):
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
        app_stack_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        prefix = f"{project_name}-{stage_name.lower()}"

        cache_bucket = s3.Bucket(
            self, "CacheBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[s3.LifecycleRule(expiration=cdk.Duration.days(7))],
        )

        # CodeBuild role:
        #   - assumes the CDK bootstrap roles to run `cdk deploy`
        #   - direct S3 + CloudFront perms for frontend sync
        #   - read CFN outputs to discover bucket/distribution names
        build_role = iam.Role(
            self, "BuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
        )
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["sts:AssumeRole"],
            resources=[f"arn:aws:iam::{self.account}:role/cdk-*"],
        ))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/*"],
        ))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["cloudformation:DescribeStacks"],
            resources=["*"],
        ))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketLocation"],
            resources=["arn:aws:s3:::*", "arn:aws:s3:::*/*"],
        ))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["cloudfront:CreateInvalidation"],
            resources=["*"],
        ))
        cache_bucket.grant_read_write(build_role)

        layer_install_cmd = (
            'REQ_SHA=$(sha256sum backend/requirements.txt | awk \'{print $1}\'); '
            'if [ -f backend/.layer.sha256 ] && [ -d backend/.layer/python ] '
            '&& [ "$(cat backend/.layer.sha256)" = "$REQ_SHA" ]; then '
            '  echo "[layer] up-to-date — skipping pip install"; '
            'else '
            '  echo "[layer] requirements.txt changed — rebuilding"; '
            '  rm -rf backend/.layer && mkdir -p backend/.layer/python; '
            '  pip install -r backend/requirements.txt -t backend/.layer/python '
            '    --platform manylinux2014_aarch64 --only-binary=:all: '
            '    --python-version 3.12 --implementation cp; '
            '  find backend/.layer -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true; '
            '  echo "$REQ_SHA" > backend/.layer.sha256; '
            'fi'
        )

        project = codebuild.PipelineProject(
            self, "Build",
            project_name=f"{prefix}-build",
            role=build_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2_STANDARD_3_0,
                compute_type=codebuild.ComputeType.SMALL,
                environment_variables={
                    "PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=project_name),
                    "GITHUB_REPO": codebuild.BuildEnvironmentVariable(value=repo),
                    "CONNECTION_ARN": codebuild.BuildEnvironmentVariable(value=connection_arn),
                },
            ),
            cache=codebuild.Cache.bucket(cache_bucket),
            timeout=cdk.Duration.minutes(30),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "cache": {
                    "paths": [
                        "/root/.cache/pip/**/*",
                        "/root/.npm/**/*",
                        "backend/.layer/**/*",
                        "backend/.layer.sha256",
                    ],
                },
                "phases": {
                    "install": {
                        "commands": ["npm install -g aws-cdk"],
                    },
                    "build": {
                        "commands": [
                            # 1. Backend tests
                            "cd backend && pip install -r requirements.txt && pytest --timeout=30 -v && cd ..",
                            # 2. Backend deps layer (skipped when requirements.txt unchanged)
                            layer_install_cmd,
                            # 3. Frontend test + build
                            "cd frontend && npm ci --prefer-offline --no-audit && npm run test -- --run && npm run build && cd ..",
                            # 4. Deploy app stack — synth + asset publish + CFN, all in one cdk process
                            "cd infra && pip install -r requirements.txt",
                            # Full CFN deploy from CodeBuild. Hotswap is for local dev
                            # (assumes the bootstrap deploy role; no extra IAM here).
                            f"cdk deploy {app_stack_name} --require-approval never",
                            "cd ..",
                            # 5. Frontend sync — read CFN outputs from the just-deployed stack
                            f'BUCKET=$(aws cloudformation describe-stacks --stack-name {app_stack_name} '
                            f'--query "Stacks[0].Outputs[?OutputKey==\'BucketName\'].OutputValue" --output text)',
                            f'DIST=$(aws cloudformation describe-stacks --stack-name {app_stack_name} '
                            f'--query "Stacks[0].Outputs[?OutputKey==\'DistributionId\'].OutputValue" --output text)',
                            'aws s3 sync frontend/dist "s3://$BUCKET" --delete',
                            'aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"',
                        ],
                    },
                },
            }),
        )

        source_artifact = codepipeline.Artifact()
        owner, repo_name = repo.split("/", 1)
        codepipeline.Pipeline(
            self, "Pipeline",
            pipeline_name=f"{prefix}-deploy",
            pipeline_type=codepipeline.PipelineType.V2,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[codepipeline_actions.CodeStarConnectionsSourceAction(
                        action_name="GitHub",
                        connection_arn=connection_arn,
                        owner=owner,
                        repo=repo_name,
                        branch=branch,
                        output=source_artifact,
                    )],
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[codepipeline_actions.CodeBuildAction(
                        action_name="DeployAll",
                        project=project,
                        input=source_artifact,
                    )],
                ),
            ],
        )
