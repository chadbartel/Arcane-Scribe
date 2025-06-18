# Standard Library
from typing import List

# Third Party
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class NewUserRequest(BaseModel):
    """
    Pydantic model for the request body when creating a new user.
    This model validates the input for the POST /users endpoint.
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
        description="The email address for the new user. This will be used for notifications."
    )
    password: str = Field(
        ...,
        min_length=8,
        description="The temporary password for the new user. The user will be required to change this on first login."
    )


class User(BaseModel):
    """
    Represents the authenticated user data decoded from the JWT.
    This model is used by dependency injection functions like `get_current_user`.
    """

    model_config = ConfigDict(populate_by_name=True)

    username: str
    email: EmailStr
    groups: List[str] = []
