#!/usr/bin/env python3
"""CDK app entry point.

Required environment variables:
  CDK_DEFAULT_ACCOUNT  — AWS account ID
  CDK_DEFAULT_REGION   — AWS region (default: us-east-1)
  PROJECT_NAME         — Project name (used for stack/pipeline naming)
  GITHUB_REPO          — GitHub repo (e.g., DatiLabs-Samples/demo-template)
  CONNECTION_ARN       — AWS CodeConnections ARN for GitHub

Stacks:
  <project>-dev-deploy   — pipeline that auto-deploys on push to `dev`
  <project>-prod-deploy  — pipeline that auto-deploys on push to `main`
  <project>-dev-app      — app resources for dev (deployed by the dev pipeline)
  <project>-prod-app     — app resources for prod (deployed by the prod pipeline)

Local bootstrap deploys only the *-deploy stacks; the *-app stacks are
deployed by their respective CodeBuild pipelines.
"""

import os
import sys
import aws_cdk as cdk
from stacks.pipeline_stack import DeployStack
from stacks.app_stack import AppStack

# The backend deps layer is asset-loaded from ../backend/.layer. The pipeline's
# build step populates it via pip install. Ensure the dir exists so local
# `cdk synth` (which never deploys the AppStack — only the deploy stacks) can
# package an empty placeholder asset without crashing.
os.makedirs(
    os.path.join(os.path.dirname(__file__), "..", "backend", ".layer", "python"),
    exist_ok=True,
)

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


def define_environment(stage_name: str, branch: str) -> None:
    app_stack_name = f"{project_name}-{stage_name.lower()}-app"

    AppStack(
        app, app_stack_name,
        env=env,
        stack_name=app_stack_name,
        project_name=project_name,
        stage_name=stage_name,
    )

    DeployStack(
        app, f"{project_name}-{stage_name.lower()}-deploy",
        env=env,
        project_name=project_name,
        repo=repo,
        branch=branch,
        stage_name=stage_name,
        connection_arn=connection_arn,
        app_stack_name=app_stack_name,
    )


define_environment("dev", "dev")
define_environment("prod", "main")

app.synth()
