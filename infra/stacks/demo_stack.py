"""Application stack — define your demo resources here.

This stack is deployed by CodePipeline, not manually.
"""

from constructs import Construct
import aws_cdk as cdk


class DemoStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # TODO: Add your demo resources here
        # Examples: Lambda, API Gateway, DynamoDB, S3, CloudFront, ECS, etc.
