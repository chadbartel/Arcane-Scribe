# Standard Library
import base64
import binascii
from typing import Dict, Any

# Third Party
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Local Modules
from core.aws import CognitoIdpClient
from core.utils.config import USER_POOL_ID, USER_POOL_CLIENT_ID
from api_authorizer import generate_policy

# Initialize logger
logger = Logger()


@logger.inject_lambda_context(log_event=False)
def lambda_handler(
    event: Dict[str, Any], context: LambdaContext
) -> Dict[str, Any]:
    """Lambda function to handle Cognito token authorization.

    Parameters
    ----------
    event : Dict[str, Any]
        The event data passed to the Lambda function, which includes
        the authorization token and method ARN.
    context : LambdaContext
        The context object containing runtime information about the
        Lambda function invocation.

    Returns
    -------
    Dict[str, Any]
        A policy document that allows or denies access based on the
        validity of the provided Cognito token.

    Raises
    ------
    Exception
        Raises an exception if the authorization fails due to
        missing or invalid token, or if there are issues with the
        Cognito client configuration.
    """
    logger.info("Cognito Token Authorizer invoked.")

    # Extract necessary information from the event
    authorization_token = event.get("authorizationToken")
    method_arn = event.get("methodArn")

    # Initialize auth response to deny access by default
    auth_response = generate_policy(
        principal_id="user", effect="Deny", resource=method_arn
    )

    # Initialize Cognito client
    cognito_client = CognitoIdpClient()

    # Check if the authorization token is provided
    if not authorization_token:
        logger.warning(
            "Authorization token not provided in request. Denying access."
        )
        raise Exception("Unauthorized")

    # Attempt to decode and validate the authorization token
    logger.info("Attempting to decode and validate authorization token.")
    try:
        # 1. Base64 decode the token
        decoded_token_bytes = base64.b64decode(authorization_token)
        decoded_token_str = decoded_token_bytes.decode("utf-8")

        # 2. Split into username and password
        if ":" not in decoded_token_str:
            logger.warning("Invalid token format: missing ':' separator.")
            raise Exception("Unauthorized")

        # Assuming the token is in the format "username:password"
        username, password = decoded_token_str.split(":", 1)

        # Add username to structured logs
        logger.append_keys(cognito_username=username)

        # Validate username and password are not empty
        if not username or not password:
            logger.warning("Username or password missing after decoding.")
            raise Exception("Unauthorized")

        # 3. Authenticate with Cognito using AdminInitiateAuth
        # (requires ADMIN_NO_SRP_AUTH on client)
        logger.info(
            f"Attempting Cognito AdminInitiateAuth for user: {username}"
        )
        cognito_response = cognito_client.admin_initiate_auth(
            user_pool_id=USER_POOL_ID,
            client_id=USER_POOL_CLIENT_ID,
            username=username,
            password=password,
        )

        # If AdminInitiateAuth succeeds, it means username/password are valid.
        if cognito_response.get("AuthenticationResult"):
            logger.info(
                f"Cognito authentication successful for user: {username}"
            )
            auth_response = generate_policy(
                principal_id=username, effect="Allow", resource=method_arn
            )
        # If AuthenticationResult is not present, it indicates a challenge
        else:
            logger.warning(
                f"Cognito authentication for user {username} did not return "
                f"AuthenticationResult. Challenge: {cognito_response.get('ChallengeName')}"
            )
            raise Exception("Unauthorized")

        # 4. Check if the authenticated user is in the 'Admins' group
        user_groups_response = cognito_client.admin_list_groups_for_user(
            user_pool_id=USER_POOL_ID,
            username=username,
        )

        # Assume user is not in 'Admins' group by default
        is_admin = False

        # Get a list of the group names
        group_names = [
            group["GroupName"] for group in user_groups_response.get("Groups", [])
        ]

        # Check if the user is in the 'Admins' group
        if "Admins" in group_names:
            is_admin = True
            logger.info(f"User {username} is in the 'Admins' group.")

        # Add context to the policy for users
        auth_response["context"] = {"isAdmin": str(is_admin).lower()}

    # Handle specific exceptions for better error reporting
    except binascii.Error as e:
        # Malformed token
        logger.warning(f"Base64 decoding error: {e}")
        raise Exception("Unauthorized")
    except UnicodeDecodeError as e:
        # Malformed token content
        logger.warning(f"UTF-8 decoding error after base64: {e}")
        raise Exception("Unauthorized")
    except ClientError as e:
        # Handle specific Cognito client errors
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "UserNotFoundException":
            logger.warning(f"Cognito user not found: {username}")
        elif error_code == "NotAuthorizedException":
            logger.warning(
                f"Cognito not authorized (e.g., incorrect password) for user: {username}"
            )
        elif error_code == "InvalidParameterException":
            logger.error(
                f"Cognito InvalidParameterException: {e}. Check "
                "UserPool/Client ID or auth params."
            )
        else:
            logger.exception(
                f"Cognito ClientError during authentication for user {username}: {e}"
            )
        raise Exception("Unauthorized")
    except Exception as e:
        # Catch-all for any other exceptions
        logger.exception(
            f"Unexpected error during token validation for user (if known) or token: {e}"
        )
        raise Exception("Unauthorized")

    return auth_response
