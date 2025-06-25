# Standard Library
from typing import Optional

# Third Party
from pydantic import BaseModel, Field, ConfigDict

# Local Modules
from core.utils import CognitoGroup


class User(BaseModel):
    """User model representing a user in the system.

    Attributes:
        username: The username of the user.
        email: The email address of the user.
        groups: List of groups the user belongs to.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(..., description="Username of the user")
    email: str = Field(..., description="Email address of the user")
    groups: list[str] = Field(
        default_factory=list, description="List of groups the user belongs to"
    )


class TokenResponse(BaseModel):
    """
    Pydantic model for the response from the /auth/login endpoint.

    Attributes:
        AccessToken: The access token issued to the user.
        ExpiresIn: The duration in seconds for which the access token is valid.
        IdToken: The ID token issued to the user.
        RefreshToken: Optional refresh token for obtaining new access tokens.
        TokenType: The type of token issued (usually "Bearer
    """

    model_config = ConfigDict(populate_by_name=True)

    # Fields for a successful login
    access_token: Optional[str] = Field(
        None, alias="AccessToken", description="Access token issued to the user"
    )
    expires_in: Optional[str] = Field(
        None,
        alias="ExpiresIn",
        description="Duration in seconds for which the access token is valid",
    )
    id_token: Optional[str] = Field(
        None, alias="IdToken", description="ID token issued to the user"
    )
    refresh_token: Optional[str] = Field(
        None,
        alias="RefreshToken",
        description="Optional refresh token for obtaining new access tokens",
    )
    token_type: Optional[str] = Field(
        "Bearer",
        alias="TokenType",
        description="The type of token issued, usually 'Bearer'",
    )

    # Fields for a new password challenge
    challenge_name: Optional[str] = Field(
        None,
        alias="ChallengeName",
        description="Name of the challenge, e.g., 'NEW_PASSWORD_REQUIRED'",
    )
    session: Optional[str] = Field(
        None,
        alias="Session",
        description="Session string for the challenge, used to respond to it",
    )

    # Pass username back to the client during a challenge
    username: Optional[str] = Field(
        None,
        alias="Username",
        description="Username of the user, returned during a challenge",
    )


class SignUpRequest(BaseModel):
    """
    Pydantic model for the admin-only user creation request body.

    Attributes:
        username: The username for the new user.
        email: The email address for the new user.
        temporary_password: A temporary password for the new user. The user will be required to change this on first login.
        user_group: Optional user group to assign the new user to. If not provided, the user will be assigned to the default 'users' group.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="The username for the new user.",
    )
    email: str = Field(..., description="The email address for the new user.")
    temporary_password: str = Field(
        ...,
        min_length=8,
        description=(
            "A temporary password for the new user. The user will be required "
            "to change this on first login."
        ),
    )
    user_group: Optional[CognitoGroup] = Field(
        CognitoGroup.users,
        description=(
            "Optional user group to assign the new user to. If not provided, "
            "the user will be assigned to the default 'users' group."
        ),
    )


class RespondToChallengeRequest(BaseModel):
    """
    Request model for responding to a Cognito authentication challenge.

    Attributes:
        username: The user's username.
        session: The session string from the Cognito challenge.
        new_password: The user's chosen new password, which must be at least 16 characters long.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(..., description="The user's username.")
    session: str = Field(
        ..., description="The session string from the Cognito challenge."
    )
    new_password: str = Field(
        ..., min_length=16, description="The user's chosen new password."
    )
