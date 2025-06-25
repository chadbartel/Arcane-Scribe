# Third Party
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

# Local Modules
from core.aws import CognitoIdpClient
from core.utils.config import USER_POOL_ID, USER_POOL_CLIENT_ID
from api_backend.models import (
    LoginRequest,
    TokenResponse,
    SignUpRequest,
    User,
    RespondToChallengeRequest,
)
from api_backend.dependencies import require_admin_user

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


@router.post("/respond-to-challenge", response_model=TokenResponse)
def respond_to_challenge(
    challenge_response: RespondToChallengeRequest,
    cognito_client: CognitoIdpClient = Depends(),
) -> JSONResponse:
    """Responds to a Cognito authentication challenge, such as a new password
    required challenge.

    **Parameters:**
    - `challenge_response`: An instance of `RespondToChallengeRequest` containing
    the username, session, and new password.

    **Returns:**
    - A JSON response containing access tokens if the challenge is successfully
    responded to.

    **Raises:**
    - `HTTPException`: If the challenge response fails, an HTTP 400 Bad Request error
    is raised with details about the failure.
    """
    try:
        tokens = cognito_client.admin_respond_to_auth_challenge(
            user_pool_id=USER_POOL_ID,
            client_id=USER_POOL_CLIENT_ID,
            username=challenge_response.username,
            session=challenge_response.session,
            new_password=challenge_response.new_password,
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=tokens)
    except ClientError as e:
        logger.error(
            f"Challenge response failed for user {challenge_response.username}: {e}"
        )
        # Provide more specific feedback if possible
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    signup_request: SignUpRequest,
    admin_user: User = Depends(require_admin_user),
    cognito_client: CognitoIdpClient = Depends(),
) -> JSONResponse:
    """
    (Admin Only) Creates a new user in the Cognito User Pool.

    **Parameters:**
    - `signup_request`: An instance of `SignUpRequest` containing the new user's
    username, email, and temporary password.
    - `admin_user`: The currently authenticated admin user, obtained via dependency injection.

    **Returns:**
    - A JSON response with a success message and user details if the user is created successfully.

    **Raises:**
    - `HTTPException`: If the user already exists, an HTTP 409 Conflict error is
    raised. If any other error occurs during user creation, an HTTP 500 Internal Server Error
    is raised.
    """
    logger.info(
        f"Admin user '{admin_user.username}' is attempting to create new user '{signup_request.username}'."
    )
    try:
        # Call the cognito client to create the user
        user_info = cognito_client.admin_create_user(
            user_pool_id=USER_POOL_ID,
            username=signup_request.username,
            email=signup_request.email,
            temporary_password=signup_request.temporary_password,
        )

        # Add user to the specified group
        cognito_client.admin_add_user_to_group(
            user_pool_id=USER_POOL_ID,
            username=signup_request.username,
            group_name=signup_request.user_group.value,
        )

        # Return a clean success response
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "User created successfully.",
                "user": {
                    "username": user_info.get("Username"),
                    "user_create_date": str(user_info.get("UserCreateDate")),
                },
            },
        )
    except cognito_client.client.exceptions.UsernameExistsException:
        logger.warning(
            f"Attempted to create a user that already exists: {signup_request.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists.",
        )
    except Exception as e:
        logger.error(f"Failed to create user {signup_request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the user.",
        )
