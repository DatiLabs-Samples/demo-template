"""CodePipeline stack — one pipeline per environment.

Dev pipeline:  watches `dev` branch, auto-deploys on push.
Prod pipeline: watches `main` branch, auto-deploys on PR merge from dev.
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
        stage_name: str,
        connection_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            pipeline_name=f"{project_name}-{stage_name.lower()}",
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

        pipeline.add_stage(
            DemoStage(self, stage_name, project_name=project_name, stage_name=stage_name, env=kwargs.get("env"))
        )


class DemoStage(cdk.Stage):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        DemoStack(self, "DemoStack", project_name=project_name, stage_name=stage_name)
