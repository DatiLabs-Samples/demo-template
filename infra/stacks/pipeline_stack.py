"""CodePipeline stack — deploy once with `cdk deploy`. After that, git push triggers deployments.

Flow: push to dev → staging deploy | merge to main → prod deploy (manual approval)
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import pipelines
from stacks.demo_stack import DemoStack


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            pipeline_name="demo-pipeline",
            synth=pipelines.ShellStep(
                "Synth",
                # TODO: Update with your repo connection ARN and repo path
                input=pipelines.CodePipelineSource.connection(
                    "owner/repo",
                    "main",
                    connection_arn="arn:aws:codeconnections:us-east-1:ACCOUNT:connection/CONNECTION_ID",
                ),
                commands=[
                    "cd backend && pip install -r requirements.txt",
                    "cd ../frontend && npm ci && npm run build",
                    "cd ../infra && pip install -r requirements.txt && npx cdk synth",
                ],
                primary_output_directory="infra/cdk.out",
            ),
        )

        # Staging
        pipeline.add_stage(DemoStage(self, "Staging", env=kwargs.get("env")))

        # Production (manual approval)
        pipeline.add_stage(
            DemoStage(self, "Prod", env=kwargs.get("env")),
            pre=[pipelines.ManualApprovalStep("PromoteToProd")],
        )


class DemoStage(cdk.Stage):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        DemoStack(self, "DemoStack")
