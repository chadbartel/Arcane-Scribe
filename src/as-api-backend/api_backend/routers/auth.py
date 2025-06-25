# Third Party
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
from aws_lambda_powertools import Logger

# Local Modules
from core.aws import CognitoIdpClient
from core.utils.config import USER_POOL_ID, USER_POOL_CLIENT_ID
from api_backend.models import LoginRequest, TokenResponse, User

# Initialize logger
logger = Logger(service="authentication")

# Initialize router for authentication endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login_for_access_token(
    login_request: LoginRequest = Body(...),
    cognito_client: CognitoIdpClient = Depends(),
) -> JSONResponse:
    """Login endpoint to authenticate users and return access tokens.

    **Parameters:**
    - `login_request`: An instance of `LoginRequest` containing the user's credentials.

    **Returns:**
    - A JSON response containing access tokens if authentication is successful.

    **Raises:**
    - `HTTPException`: If authentication fails, an HTTP 401 Unauthorized error
    is raised.
    """
    try:
        logger.info(f"Attempting to log in user: {login_request.username}")
        tokens = cognito_client.admin_initiate_auth(
            user_pool_id=USER_POOL_ID,
            client_id=USER_POOL_CLIENT_ID,
            username=login_request.username,
            password=login_request.password,
        )
        logger.info(f"User {login_request.username} logged in successfully.")
        return JSONResponse(status_code=status.HTTP_200_OK, content=tokens)
    except Exception as e:
        logger.error(f"Login failed for user {login_request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect username or password: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/user", response_model=User)
def get_current_user(
    cognito_client: CognitoIdpClient = Depends(),
) -> JSONResponse:
    """Endpoint to retrieve the current authenticated user's information.

    **Returns:**
    - An instance of `User` containing the user's details.

    **Raises:**
    - `HTTPException`: If the user is not authenticated, an HTTP 401 Unauthorized
    error is raised.
    """
    try:
        user = User.model_validate(cognito_client.get_current_user())
        logger.info(f"Retrieved user info for {user.username}.")
        return JSONResponse(
            status_code=status.HTTP_200_OK, content=user.model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to retrieve user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
        )
