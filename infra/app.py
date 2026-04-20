#!/usr/bin/env python3
"""CDK app entry point.

Required environment variables:
  CDK_DEFAULT_ACCOUNT  — AWS account ID
  CDK_DEFAULT_REGION   — AWS region (default: us-east-1)
  PROJECT_NAME         — Project name (used for stack/pipeline naming)
  GITHUB_REPO          — GitHub repo (e.g., DatiLabs-Samples/demo-template)
  CONNECTION_ARN       — AWS CodeConnections ARN for GitHub

Pipelines:
  dev branch  → Dev stage (auto-deploy on push)
  main branch → Prod stage (auto-deploy on PR merge)
"""

import os
import sys
import aws_cdk as cdk
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

project_name = os.environ.get("PROJECT_NAME")
repo = os.environ.get("GITHUB_REPO")
connection_arn = os.environ.get("CONNECTION_ARN")

if not all([project_name, repo, connection_arn]):
    print("ERROR: Missing required environment variables:")
    print("  export PROJECT_NAME=my-demo")
    print("  export GITHUB_REPO=Org/repo")
    print("  export CONNECTION_ARN=arn:aws:codeconnections:...")
    sys.exit(1)

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

# Dev pipeline — triggered by push to dev branch
PipelineStack(
    app,
    f"{project_name}-dev-pipeline",
    env=env,
    project_name=project_name,
    repo=repo,
    branch="dev",
    stage_name="Dev",
    connection_arn=connection_arn,
)

# Prod pipeline — triggered by PR merge to main branch
PipelineStack(
    app,
    f"{project_name}-prod-pipeline",
    env=env,
    project_name=project_name,
    repo=repo,
    branch="main",
    stage_name="Prod",
    connection_arn=connection_arn,
)

app.synth()
