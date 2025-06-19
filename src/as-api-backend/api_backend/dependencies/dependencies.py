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


def verify_source_ip(request: Request) -> None:
    """Verifies the source IP of the request against a whitelisted IP from SSM.

    Parameters
    ----------
    request : Request
        The FastAPI request object containing the source IP.

    Raises
    ------
    HTTPException
        If the source IP is not whitelisted or cannot be determined.
        - 403 Forbidden if the IP does not match the whitelist.
        - 503 Service Unavailable if the SSM parameter cannot be fetched.
    """
    # Initialize the source IP to None
    source_ip = None

    # For API Gateway with Lambda Proxy integration (works for both REST and HTTP APIs)
    if "requestContext" in request.scope.get("aws.event", {}):
        source_ip = request.scope["aws.event"]["requestContext"][
            "identity"
        ].get("sourceIp")

    # Fallback for local testing where Uvicorn sets `request.client`
    if not source_ip and request.client:
        source_ip = request.client.host

    # Log the source IP for debugging
    logger.append_keys(source_ip=source_ip)
    logger.info("Executing IP whitelist check.")

    # If source IP is still None, raise an error
    if not source_ip:
        logger.warning("Source IP could not be determined from the request.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not determine client IP address.",
        )

    # Fetch the allowed IP from SSM
    allowed_ip = get_allowed_ip_from_ssm()

    # If allowed IP is None, raise an error
    if not allowed_ip:
        logger.error(
            "Whitelist IP could not be loaded from configuration. Denying access by default."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Service is temporarily unavailable due to a configuration issue."
            ),
        )

    # If the source IP does not match the allowed IP, raise an error
    if source_ip != allowed_ip:
        logger.warning(
            f"Forbidden access for IP: {source_ip}. Whitelisted IP is {allowed_ip}."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access from your IP address is not permitted.",
        )

    # If the source IP matches the allowed IP, log success
    logger.info(
        f"IP address {source_ip} successfully verified against whitelist."
    )


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
