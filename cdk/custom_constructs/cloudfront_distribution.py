# Standard Library
from typing import Optional

# Third Party
from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
)
from constructs import Construct


class CustomCdn(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        name: str,
        s3_origin: s3.IBucket,
        domain_name: str,
        api_certificate: acm.ICertificate,
        origin_access_identity: Optional[cloudfront.IOriginAccessIdentity] = None,
        stack_suffix: Optional[str] = "",
        default_root_object: Optional[str] = "index.html",
    ) -> None:
        """Custom CloudFront Distribution Construct for AWS CDK.

        Parameters
        ----------
        scope : Construct
            The scope in which this construct is defined.
        id : str
            The ID of the construct.
        name : str
            The name of the CloudFront distribution.
        s3_origin : s3.IBucket
            The S3 bucket to use as the origin for the CloudFront distribution.
        stack_suffix : Optional[str], optional
            Suffix to append to the CloudFront distribution name, by default ""
        default_root_object : Optional[str], optional
            The default root object for the CloudFront distribution, by default "index.html"
        """
        super().__init__(scope, id)

        # Append stack suffix to name if provided
        if stack_suffix:
            name = f"{name}{stack_suffix}"

        # Create a CloudFront distribution with the specified S3 origin
        self.distribution = cloudfront.Distribution(
            self,
            id,
            default_root_object=default_root_object,
            # Default behavior to serve content from S3 bucket
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    s3_origin,
                    origin_access_identity=origin_access_identity,
                ),
                viewer_protocol_policy=(
                    cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
                ),
                allowed_methods=(
                    cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS
                ),
                cached_methods=(
                    cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS
                ),
                compress=True,
            ),
            domain_names=[domain_name],
            certificate=api_certificate,
            comment=name,
            enable_logging=True,
            log_bucket=s3_origin,  # Use the same S3 bucket for logging
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )
