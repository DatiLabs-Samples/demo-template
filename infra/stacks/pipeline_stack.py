"""CodePipeline stack — deploy once with `cdk deploy`. After that, git push triggers deployments.

Flow: push to branch → staging deploy → manual approval → prod deploy
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import pipelines
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
        connection_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            pipeline_name=f"{project_name}-pipeline",
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.connection(
                    repo,
                    branch,
                    connection_arn=connection_arn,
                ),
                install_commands=[
                    "npm install -g aws-cdk",
                ],
                commands=[
                    "cd backend && pip install -r requirements.txt",
                    "cd ../frontend && npm ci && npm run build",
                    "cd ../infra && pip install -r requirements.txt && cdk synth",
                ],
                primary_output_directory="infra/cdk.out",
            ),
        )

        # Staging
        pipeline.add_stage(
            DemoStage(self, "Staging", project_name=project_name, env=kwargs.get("env"))
        )

        # Production (manual approval)
        pipeline.add_stage(
            DemoStage(self, "Prod", project_name=project_name, env=kwargs.get("env")),
            pre=[pipelines.ManualApprovalStep("PromoteToProd")],
        )


class DemoStage(cdk.Stage):
    def __init__(self, scope: Construct, id: str, *, project_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        DemoStack(self, "DemoStack", project_name=project_name)
