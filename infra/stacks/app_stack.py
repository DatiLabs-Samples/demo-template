"""Application stack — Backend (Lambda LWA + API GW) + Frontend (S3 + CloudFront)."""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_route53 as route53,
)

# CloudFront's global hosted zone ID — fixed for all alias records targeting CloudFront.
CLOUDFRONT_HOSTED_ZONE_ID = "Z2FDTNDATAQYW2"


class AppStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        stage_name: str,
        domain: str | None = None,
        certificate_arn: str | None = None,
        hosted_zone_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        cdk.Tags.of(self).add("Project", project_name)
        cdk.Tags.of(self).add("Environment", stage_name)

        prefix = f"{project_name}-{stage_name.lower()}"

        # --- Backend ---
        lwa_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "LWALayer",
            f"arn:aws:lambda:{self.region}:753240598075:layer:LambdaAdapterLayerArm64:24",
        )

        # Deps layer — pre-built into ../backend/.layer/python by the pipeline's
        # synth step. Asset SOURCE hash is stable when requirements.txt is
        # unchanged, so unchanged builds skip the S3 upload.
        backend_deps_layer = _lambda.LayerVersion(
            self, "BackendDepsLayer",
            layer_version_name=f"{prefix}-backend-deps",
            code=_lambda.Code.from_asset("../backend/.layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            compatible_architectures=[_lambda.Architecture.ARM_64],
        )

        backend_fn = _lambda.Function(
            self, "BackendFn",
            function_name=f"{prefix}-backend",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="run.sh",
            code=_lambda.Code.from_asset("../backend",
                exclude=[
                    "venv", ".pytest_cache", "tests", "__pycache__", "*.pyc",
                    ".env*", "pyproject.toml", ".layer", ".layer.sha256",
                    "requirements*.txt",
                ],
            ),
            layers=[lwa_layer, backend_deps_layer],
            memory_size=256,
            timeout=cdk.Duration.seconds(30),
            environment={
                "AWS_LAMBDA_EXEC_WRAPPER": "/opt/bootstrap",
                "AWS_LWA_PORT": "8000",
                "CORS_ORIGINS": "*",
                # Layer deps live at /opt/python; LWA invokes run.sh which
                # spawns a fresh Python that doesn't get Lambda's automatic
                # layer-on-sys.path injection — set it explicitly here.
                "PYTHONPATH": "/opt/python",
            },
        )

        api = apigwv2.HttpApi(self, "BackendApi", api_name=f"{prefix}-api")
        api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=integrations.HttpLambdaIntegration("BackendIntegration", backend_fn),
        )

        # --- Frontend ---
        bucket = s3.Bucket(
            self, "FrontendBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        api_origin = origins.HttpOrigin(
            f"{api.api_id}.execute-api.{self.region}.amazonaws.com",
        )

        api_behavior = cloudfront.BehaviorOptions(
            origin=api_origin,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        )

        # Custom domain: prod uses {domain} as-is; dev gets a `dev.` prefix.
        custom_domain: str | None = None
        certificate = None
        if domain:
            if not certificate_arn:
                raise ValueError("certificate_arn is required when domain is set")
            custom_domain = domain if stage_name.lower() == "prod" else f"{stage_name.lower()}.{domain}"
            certificate = acm.Certificate.from_certificate_arn(self, "Cert", certificate_arn)

        distribution = cloudfront.Distribution(
            self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/health": api_behavior,
                "/api/*": api_behavior,
            },
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403, response_page_path="/index.html", response_http_status=200,
                ),
                cloudfront.ErrorResponse(
                    http_status=404, response_page_path="/index.html", response_http_status=200,
                ),
            ],
            domain_names=[custom_domain] if custom_domain else None,
            certificate=certificate,
        )

        if custom_domain and hosted_zone_id:
            for record_type in ("A", "AAAA"):
                route53.CfnRecordSet(
                    self, f"AliasRecord{record_type}",
                    hosted_zone_id=hosted_zone_id,
                    name=custom_domain,
                    type=record_type,
                    alias_target=route53.CfnRecordSet.AliasTargetProperty(
                        dns_name=distribution.distribution_domain_name,
                        hosted_zone_id=CLOUDFRONT_HOSTED_ZONE_ID,
                        evaluate_target_health=False,
                    ),
                )

        # --- Outputs ---
        cdk.CfnOutput(self, "ApiUrl", value=api.url or "")
        self.bucket_name_output = cdk.CfnOutput(self, "BucketName", value=bucket.bucket_name)
        self.distribution_id_output = cdk.CfnOutput(self, "DistributionId", value=distribution.distribution_id)
        cdk.CfnOutput(self, "DistributionDomainName", value=distribution.distribution_domain_name)
        if custom_domain:
            cdk.CfnOutput(self, "CustomDomain", value=custom_domain)
