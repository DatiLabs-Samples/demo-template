"""Application stack — S3 + CloudFront for frontend hosting."""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3, aws_cloudfront as cloudfront, aws_cloudfront_origins as origins


class DemoStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, *, project_name: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cdk.Tags.of(self).add("Project", project_name)
        cdk.Tags.of(self).add("Environment", stage_name)

        bucket = s3.Bucket(
            self, "FrontendBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
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
