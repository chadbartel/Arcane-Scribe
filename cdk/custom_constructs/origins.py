# Standard Library
from typing import Optional, Dict

# Third Party
from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct


class CustomS3Origin(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        bucket: s3.IBucket,
        origin_access_control: Optional[cloudfront.IOriginAccessControl] = None,
        origin_access_identity: Optional[cloudfront.IOriginAccessIdentity] = None,
        origin_path: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Custom S3 Origin Construct for AWS CDK.

        Parameters
        ----------
        scope : Construct
            The scope in which this construct is defined.
        id : str
            The ID of the construct.
        bucket : s3.IBucket
            The S3 bucket to use as the origin.
        origin_access_control : Optional[cloudfront.IOriginAccessControl], optional
            The CloudFront Origin Access Control for the S3 bucket, by default None
        origin_access_identity : Optional[cloudfront.IOriginAccessIdentity], optional
            The CloudFront Origin Access Identity for the S3 bucket (legacy), by default None
        origin_path : Optional[str], optional
            The path within the S3 bucket to use as the origin, by default None
        custom_headers : Optional[Dict[str, str]], optional
            Custom headers to include in the origin request, by default None
        """
        super().__init__(scope, id)

        # Create the S3 origin for CloudFront
        if origin_access_control is not None:
            # Use Origin Access Control (OAC) - recommended approach
            self.origin = origins.S3BucketOrigin.with_origin_access_control(
                bucket,
                origin_access_control=origin_access_control,
                origin_path=origin_path,
                custom_headers=custom_headers,
            )
        elif origin_access_identity is not None:
            # Use Origin Access Identity (OAI) - legacy approach
            self.origin = origins.S3BucketOrigin.with_origin_access_identity(
                bucket,
                origin_access_identity=origin_access_identity,
                origin_path=origin_path,
                custom_headers=custom_headers,
            )
        else:
            # Use default bucket settings (no access control)
            self.origin = origins.S3BucketOrigin.with_bucket_defaults(
                bucket,
                origin_path=origin_path,
                custom_headers=custom_headers,
            )


class CustomHttpOrigin(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        domain_name: str,
        origin_path: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Custom HTTP Origin Construct for AWS CDK.

        Parameters
        ----------
        scope : Construct
            The scope in which this construct is defined.
        id : str
            The ID of the construct.
        domain_name : str
            The domain name of the HTTP origin.
        origin_path : Optional[str], optional
            The path within the HTTP origin, by default None
        custom_headers : Optional[dict], optional
            Custom headers to include in the origin request, by default None
        custom_origin_config : Optional[cloudfront.CustomOriginConfig], optional
            Custom configuration for the HTTP origin, by default None
        """
        super().__init__(scope, id)

        # Create the HTTP origin for CloudFront
        self.origin = origins.HttpOrigin(
            domain_name,
            origin_path=origin_path,
            custom_headers=custom_headers,
        )
