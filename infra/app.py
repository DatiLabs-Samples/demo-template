#!/usr/bin/env python3
"""CDK app entry point.

Required environment variables (or cdk.json context):
  CDK_DEFAULT_ACCOUNT  — AWS account ID for deployment
  CDK_DEFAULT_REGION   — AWS region (default: us-east-1)

Required CDK context (pass via -c or cdk.json):
  project_name         — Project name (used for stack/pipeline naming)
  repo                 — GitHub repo path (e.g., DatiLabs-Samples/demo-template)
  connection_arn       — AWS CodeConnections ARN for GitHub
  branch               — Git branch to deploy from (default: main)
"""

import os
import sys
import aws_cdk as cdk
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

# --- Required context ---
project_name = app.node.try_get_context("project_name")
repo = app.node.try_get_context("repo")
connection_arn = app.node.try_get_context("connection_arn")
branch = app.node.try_get_context("branch") or "main"

if not all([project_name, repo, connection_arn]):
    print("ERROR: Missing required CDK context. Set in cdk.json or pass via -c:")
    print("  cdk deploy -c project_name=my-demo -c repo=Org/repo -c connection_arn=arn:aws:...")
    sys.exit(1)

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

PipelineStack(
    app,
    f"{project_name}-pipeline",
    env=env,
    project_name=project_name,
    repo=repo,
    branch=branch,
    connection_arn=connection_arn,
)

app.synth()
