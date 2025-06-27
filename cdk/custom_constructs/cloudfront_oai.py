# Standard Library
from typing import Optional

# Third Party
from aws_cdk import aws_cloudfront as cloudfront
from constructs import Construct


class CustomOai(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        comment: Optional[str] = "Custom CloudFront OAI",
    ) -> None:
        """Custom CloudFront Origin Access Identity (OAI) Construct for AWS CDK.

        Parameters
        ----------
        scope : Construct
            The scope in which this construct is defined.
        id : str
            The ID of the construct.
        comment : Optional[str], optional
            A comment for the OAI, by default "Custom CloudFront OAI"
        """
        super().__init__(scope, id)

        # Create a CloudFront Origin Access Identity
        self.oai = cloudfront.OriginAccessIdentity(
            self,
            id,
            comment=comment,
        )
