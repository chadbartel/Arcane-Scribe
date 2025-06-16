"""This module initializes the AWS-related components for the PDF ingestor service."""

# Local Modules
from pdf_ingestor.aws.dynamodb import DynamoDb

__all__ = ["DynamoDb"]
