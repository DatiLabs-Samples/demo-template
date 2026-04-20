"""Frontend stack — S3 + CloudFront, routes /health and /api/* to backend API."""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigatewayv2 as apigwv2,
)


class FrontendStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str,
                 api: apigwv2.HttpApi, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cdk.Tags.of(self).add("Project", project_name)
        cdk.Tags.of(self).add("Environment", stage_name)

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
        )

        self.bucket_name_output = cdk.CfnOutput(self, "BucketName", value=bucket.bucket_name)
        self.distribution_id_output = cdk.CfnOutput(self, "DistributionId", value=distribution.distribution_id)
        cdk.CfnOutput(self, "DistributionDomainName", value=distribution.distribution_domain_name)
