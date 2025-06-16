"""Core AWS modules for the Arcane Scribe API.

This module provides AWS-related functionality for the Arcane Scribe API,
including clients for DynamoDB, SSM, S3, and Bedrock. It allows for
easy access to these services without needing to import them individually in
other parts of the codebase.
"""

# Local Modules
from core.aws.s3 import S3Client
from core.aws.ssm import SsmClient
from core.aws.dynamodb import DynamoDb
from core.aws.bedrock_runtime import BedrockRuntimeClient
from core.aws.cognito import CognitoIdpClient

__all__ = [
    "S3Client",
    "SsmClient",
    "DynamoDb",
    "BedrockRuntimeClient",
    "CognitoIdpClient",
]
