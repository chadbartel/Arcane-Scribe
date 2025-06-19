"""Pydantic models for authentication requests."""

# Third Party
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """LoginRequest model for user authentication.

    Attributes:
        username: User's username for login.
        password: User's password for login.
    """
    username: str = Field(..., description="User's username")
    password: str = Field(..., description="User's password")
