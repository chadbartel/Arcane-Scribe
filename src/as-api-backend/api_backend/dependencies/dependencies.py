# Standard Library
from typing import Optional

# Third Party
from fastapi import Request, HTTPException, status, Depends
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

# Local Modules
from core.aws import SsmClient
from core.utils.config import HOME_IP_SSM_PARAMETER_NAME
from api_backend.models import User

# Initialize logger
logger = Logger(service="dependencies")


def get_allowed_ip_from_ssm() -> Optional[str]:
    """Fetches the allowed IP from SSM, using a short-lived in-memory cache.

    Returns
    -------
    Optional[str]
        The allowed IP address as a string if found, otherwise None.
    """
    try:
        # Get the SSM client
        ssm_client = SsmClient()

        # Get the SSM parameter value from the environment variable
        ip_address = ssm_client.get_parameter(name=HOME_IP_SSM_PARAMETER_NAME)

        # Return the IP address if it exists
        if ip_address and isinstance(ip_address, str):
            return ip_address
        else:
            # If the parameter value is empty, log an error and return None
            logger.error("SSM parameter value is empty or not found.")
            return None
    except ClientError as e:
        # Handle specific SSM client errors
        logger.exception(
            f"Error fetching IP from SSM parameter '{HOME_IP_SSM_PARAMETER_NAME}': {e}"
        )
    return None


def verify_source_ip(request: Request) -> bool:
    """Verifies the source IP of the request against a whitelisted IP from SSM.

    Parameters
    ----------
    request : Request
        The FastAPI request object containing the source IP.

    Returns
    -------
    bool
        True if the source IP matches the whitelisted IP, otherwise raises an
        HTTPException.

    Raises
    ------
    HTTPException
        If the source IP is not whitelisted or cannot be determined.
        - 403 Forbidden if the IP does not match the whitelist.
        - 503 Service Unavailable if the SSM parameter cannot be fetched.
    """
    # Initialize the source IP to None
    source_ip = None  # For API Gateway with Lambda Proxy integration (works for both REST and HTTP APIs)

    # Prioritize the X-Forwarded-For header added by CloudFront
    #  The header can contain a list of IPs, the original client is the first one.
    if "x-forwarded-for" in request.headers:
        source_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        logger.info(f"Found source IP in X-Forwarded-For header: {source_ip}")
    else:
        # Fallback to the direct source IP from API Gateway context
        try:
            source_ip = request.scope["aws.event"]["requestContext"][
                "identity"
            ]["sourceIp"]
            logger.info(f"Using source IP from requestContext: {source_ip}")
        except KeyError:
            logger.error("Could not find 'sourceIp' in request context.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: Cannot determine source IP.",
            )

    # Get the allowed IP from SSM Parameter Store
    whitelisted_ip = get_allowed_ip_from_ssm()

    # Compare the IPs and raise an exception if they don't match
    logger.info(
        f"Verifying request source IP '{source_ip}' against whitelisted IP '{whitelisted_ip}'."
    )
    if source_ip != whitelisted_ip:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access from your IP address is not permitted.",
        )

    return True


def get_current_user(request: Request) -> User:
    """Retrieves the current user from the request context, extracting
    user information from the JWT claims provided by the API Gateway.

    Parameters
    ----------
    request : Request
        The FastAPI request object containing the JWT claims.

    Returns
    -------
    User
        A User model instance containing the username, email, and groups of the
        user.

    Raises
    ------
    HTTPException
        If the JWT claims are missing or invalid, a 401 Unauthorized error is
        raised.
        - 401 Unauthorized if the JWT claims are missing or invalid.
    """
    try:
        # API Gateway passes claims here after validating the JWT
        claims = request.scope["aws.event"]["requestContext"]["authorizer"][
            "claims"
        ]

        # The 'cognito:groups' claim is an array of group names
        user_groups = claims.get("cognito:groups", [])

        return User(
            username=claims["cognito:username"],
            email=claims["email"],
            groups=(
                [user_groups] if isinstance(user_groups, str) else user_groups
            ),
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Claims missing.",
        )


def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verifies that the current user has admin privileges by checking
    if the user belongs to the "Admins" group.

    Parameters
    ----------
    current_user : User, optional
        The current user object, automatically injected by FastAPI's dependency
        injection system. Defaults to the result of `get_current_user()`.

    Returns
    -------
    User
        The current user object if the user has admin privileges.

    Raises
    ------
    HTTPException
        If the user does not have admin privileges, a 403 Forbidden error is
        raised.
        - 403 Forbidden if the user does not belong to the "Admins" group.
    """
    if "Admins" not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have admin privileges.",
        )

    return current_user
