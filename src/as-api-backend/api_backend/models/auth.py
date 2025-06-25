# Standard Library
from typing import Optional

# Third Party
from pydantic import BaseModel, Field, ConfigDict


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
