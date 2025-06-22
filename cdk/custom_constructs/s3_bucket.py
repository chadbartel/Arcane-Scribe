# Standard Library
from typing import Optional, List

# Third Party
from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_s3_deployment as s3_deployment,
)
from constructs import Construct


class CustomS3Bucket(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        name: str,
        stack_suffix: Optional[str] = "",
        versioned: Optional[bool] = False,
        lifecycle_rules: Optional[List[s3.LifecycleRule]] = None,
        event_bridge_enabled: Optional[bool] = False,
        public_read_access: Optional[bool] = False,
        website_index_document: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Custom S3 Bucket Construct for AWS CDK.

        Parameters
        ----------
        scope : Construct
            The scope in which this construct is defined.
        id : str
            The ID of the construct.
        name : str
            The name of the S3 bucket.
        stack_suffix : Optional[str], optional
            Suffix to append to the S3 bucket name, by default ""
        versioned : Optional[bool], optional
            Whether the S3 bucket should be versioned, by default False
        lifecycle_rules : Optional[List[s3.LifecycleRule]], optional
            Lifecycle rules for the S3 bucket, by default None
        event_bridge_enabled : Optional[bool], optional
            Whether to enable EventBridge for the S3 bucket, by default False
        public_read_access : Optional[bool], optional
            Whether to allow public read access to the S3 bucket, by default False
        website_index_document : Optional[str], optional
            The index document for the S3 bucket if it is a static website, by default None
        """
        super().__init__(scope, id, **kwargs)

        # Append stack suffix to name if provided
        if stack_suffix:
            name = f"{name}{stack_suffix}"

        # Set default lifecycle rules if not provided
        if lifecycle_rules is None:
            lifecycle_rules = [
                # Intelligent Tiering rule
                s3.LifecycleRule(
                    id="DefaultIntelligentTiering",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(0),
                        )
                    ],
                ),
                # Abort incomplete multipart uploads rule
                s3.LifecycleRule(
                    id="AbortIncompleteMultipartUploads",
                    enabled=True,
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                ),
            ]

        # Create the S3 bucket
        self.bucket = s3.Bucket(
            self,
            "DefaultBucket",
            bucket_name=name,
            versioned=versioned,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=lifecycle_rules,
            event_bridge_enabled=event_bridge_enabled,
            public_read_access=public_read_access,
            website_index_document=website_index_document,
        )


class CustomBucketDeployment(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        destination_bucket: s3.IBucket,
        source: str,
        distribution: Optional[cloudfront.IDistribution] = None,
        distribution_paths: Optional[List[str]] = ["/*"],
    ) -> None:
        """Custom Bucket Deployment Construct for AWS CDK.

        Parameters
        ----------
        scope : Construct
            The scope in which this construct is defined.
        id : str
            The ID of the construct.
        destination_bucket : s3.IBucket
            The S3 bucket where the contents will be deployed.
        source : str
            The local path to the source directory containing the files to deploy.
        distribution : Optional[cloudfront.IDistribution], optional
            The CloudFront distribution to invalidate after deployment, by default None
        distribution_paths : Optional[List[str]], optional
            The paths to invalidate in the CloudFront distribution, by default ["/*"]
        """
        super().__init__(scope, id)

        # Deploy the contents from the source bucket to the target bucket
        self.deployment = s3_deployment.BucketDeployment(
            self,
            "DeployBucketContents",
            sources=[s3_deployment.Source.asset(source)],
            destination_bucket=destination_bucket,
            distribution=distribution,
            distribution_paths=distribution_paths,
            retain_on_delete=False,  # Remove contents on deletion
        )
