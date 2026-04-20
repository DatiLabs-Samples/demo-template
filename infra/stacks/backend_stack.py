"""Backend stack — Lambda Web Adapter (FastAPI) + HTTP API Gateway."""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
)


class BackendStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cdk.Tags.of(self).add("Project", project_name)
        cdk.Tags.of(self).add("Environment", stage_name)

        lwa_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "LWALayer",
            f"arn:aws:lambda:{self.region}:753240598075:layer:LambdaAdapterLayerArm64:24",
        )

        backend_fn = _lambda.Function(
            self, "BackendFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="run.sh",
            code=_lambda.Code.from_asset("../backend", bundling=cdk.BundlingOptions(
                image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                command=["bash", "-c",
                    "pip install --no-cache-dir -r requirements.txt -t /asset-output"
                    " && cp -r app /asset-output/"
                    " && cp run.sh /asset-output/"
                ],
            )),
            layers=[lwa_layer],
            memory_size=256,
            timeout=cdk.Duration.seconds(30),
            environment={
                "AWS_LAMBDA_EXEC_WRAPPER": "/opt/bootstrap",
                "AWS_LWA_PORT": "8000",
                "CORS_ORIGINS": "*",
            },
        )

        self.api = apigwv2.HttpApi(self, "BackendApi")
        self.api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=integrations.HttpLambdaIntegration("BackendIntegration", backend_fn),
        )

        cdk.CfnOutput(self, "ApiUrl", value=self.api.url or "")
