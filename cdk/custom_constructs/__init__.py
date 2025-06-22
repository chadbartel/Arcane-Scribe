"""This module provides custom constructs for AWS CDK applications.

These constructs extend the functionality of AWS CDK by providing reusable
components for common AWS services such as API Gateway, Lambda, DynamoDB, S3,
and IAM. Each construct is designed to simplify the creation and management of
AWS resources with sensible defaults and additional features.

The constructs included in this module are:
- ApiCustomDomain: Custom domain for API Gateway.
- CustomDynamoDBTable: Custom DynamoDB table with additional configurations.
- CustomHttpApiGateway: Custom HTTP API Gateway with enhanced features.
- CustomHttpLambdaAuthorizer: Custom HTTP Lambda authorizer for API Gateway.
- CustomIAMPolicyStatement: Custom IAM policy statement for fine-grained access control.
- CustomIamRole: Custom IAM role with specific permissions.
- CustomLambdaFromDockerImage: Custom Lambda function created from a Docker image.
- CustomLambdaFunction: Custom Lambda function with additional configurations.
- CustomRestApi: Custom REST API Gateway with additional configurations.
- CustomS3Bucket: Custom S3 bucket with additional configurations.
- CustomTokenAuthorizer: Custom token authorizer for API Gateway.
- CustomCognitoUserPool: Custom Cognito User Pool with additional configurations.
- CognitoAdminUser: Custom construct for managing an admin user in a Cognito User Pool.
"""

from .api_custom_domain import ApiCustomDomain
from .dynamodb_table import CustomDynamoDBTable
from .http_api import CustomHttpApiGateway
from .http_lambda_authorizer import CustomHttpLambdaAuthorizer
from .iam_policy_statement import CustomIAMPolicyStatement
from .iam_role import CustomIamRole
from .lambda_function import CustomLambdaFromDockerImage, CustomLambdaFunction
from .rest_api import CustomRestApi
from .s3_bucket import CustomS3Bucket, CustomBucketDeployment
from .token_authorizer import CustomTokenAuthorizer
from .cognito_user_pool import CustomCognitoUserPool
from .cognito_admin_user import CognitoAdminUser
from .cloudfront_distribution import CustomCdn
from .cloudfront_oai import CustomOai

__all__ = [
    "ApiCustomDomain",
    "CustomHttpApiGateway",
    "CustomDynamoDBTable",
    "CustomHttpLambdaAuthorizer",
    "CustomIAMPolicyStatement",
    "CustomIamRole",
    "CustomLambdaFromDockerImage",
    "CustomLambdaFunction",
    "CustomRestApi",
    "CustomS3Bucket",
    "CustomTokenAuthorizer",
    "CustomCognitoUserPool",
    "CognitoAdminUser",
    "CustomCdn",
    "CustomBucketDeployment",
    "CustomOai",
]
