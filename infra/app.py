#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

PipelineStack(app, "DemoPipelineStack", env=env)

app.synth()
