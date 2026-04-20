"""Application stack — define your demo resources here."""

from constructs import Construct
import aws_cdk as cdk


class DemoStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cdk.Tags.of(self).add("Project", project_name)
        cdk.Tags.of(self).add("Environment", stage_name)

        # TODO: Add your demo resources here
