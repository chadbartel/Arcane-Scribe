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
