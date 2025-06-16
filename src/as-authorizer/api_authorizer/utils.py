# Standard Library
from typing import Dict, Any, Optional

# Third Party
from aws_lambda_powertools import Logger

# Initialize logger
logger = Logger(service="cck-api-authorizer-utils")


def generate_policy(
    principal_id: str,
    effect: str,
    resource: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate an IAM policy for the API Gateway authorizer.

    Parameters
    ----------
    principal_id : str
        The principal ID of the user or entity being authorized.
    effect : str
        The effect of the policy, either "Allow" or "Deny".
    resource : str
        The resource ARN that the policy applies to.
    context : Optional[Dict[str, Any]], optional
        Additional context to include in the policy, by default None

    Returns
    -------
    Dict[str, Any]
        A dictionary representing the IAM policy for the API Gateway
        authorizer.
    """
    # Generate an IAM policy for the API Gateway authorizer.
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource,
                }
            ],
        },
    }

    # Add context if provided
    if context is not None:
        policy["context"] = context
    return policy
