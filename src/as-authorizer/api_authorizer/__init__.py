"""
Arcane Scribe API Authorizer

This module provides utilities for a custom Lambda authorizer that validates
API requests against AWS Cognito user pools. It includes functions to get the
Cognito client, generate IAM policies, and log events.
"""

# Local Modules
from .utils import (
    generate_policy,
    logger,
)

__all__ = [
    "generate_policy",
    "logger",
]
