# Standard Library
from typing import Optional

# Third Party
from pydantic import BaseModel, Field, ConfigDict, EmailStr


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

    access_token: str = Field(
        ..., alias="AccessToken", description="Access token issued to the user"
    )
    expires_in: int = Field(
        ...,
        alias="ExpiresIn",
        description="Duration in seconds for which the access token is valid",
    )
    id_token: str = Field(
        ..., alias="IdToken", description="ID token issued to the user"
    )
    refresh_token: Optional[str] = Field(
        None,
        alias="RefreshToken",
        description="Optional refresh token for obtaining new access tokens",
    )
    token_type: str = Field(
        "Bearer",
        alias="TokenType",
        description="The type of token issued, usually 'Bearer'",
    )


class SignUpRequest(BaseModel):
    """
    Pydantic model for the admin-only user creation request body.

    Attributes:
        username: The username for the new user.
        email: The email address for the new user.
        temporary_password: A temporary password for the new user. The user will be required to change this on first login.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="The username for the new user."
    )
    email: EmailStr = Field(
        ...,
        description="The email address for the new user."
    )
    temporary_password: str = Field(
        ...,
        min_length=8,
        description=(
            "A temporary password for the new user. The user will be required "
            "to change this on first login."
        )
    )
