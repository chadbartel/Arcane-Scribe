# Standard Library
from typing import Optional

# Third Party
from pydantic import BaseModel, Field, ConfigDict, HttpUrl, UUID4

# Local Modules
from core.utils import AllowedMethod


class PresignedUrlRequest(BaseModel):
    """Pydantic model for presigned URL generation requests.

    Attributes:
        file_name: The name of the file to upload.
        content_type: Optional content type for the file.
    """

    model_config = ConfigDict(populate_by_name=True)

    file_name: str = Field(
        ...,
        description="The name of the file to upload.",
    )
    content_type: Optional[str] = Field(
        "application/pdf",
        description=("Content type for the file."),
        examples=["application/pdf"],
    )


class PresignedUrlResponse(BaseModel):
    """Pydantic model for presigned URL generation responses.

    Attributes:
        presigned_url: The generated presigned URL for file upload.
        bucket_name: The name of the S3 bucket.
        key: The object key in the S3 bucket.
        expires_in: The expiration time in seconds.
        method: The HTTP method for the upload operation.
        srd_id: The ID of the SRD document.
        document_id: A unique identifier for the document.
        content_type: Content type for the file.
    """

    model_config = ConfigDict(populate_by_name=True)

    presigned_url: HttpUrl = Field(
        ...,
        description="The generated presigned URL for file upload.",
    )
    bucket_name: str = Field(
        ...,
        description="The name of the S3 bucket.",
    )
    key: str = Field(
        ...,
        description="The object key in the S3 bucket.",
    )
    expires_in: int = Field(
        ...,
        description="The expiration time in seconds.",
    )
    method: AllowedMethod = Field(
        ..., description="The HTTP method for the upload operation."
    )
    srd_id: str = Field(
        ...,
        description="The ID of the SRD document.",
        examples=["dnd_5e"],
    )
    document_id: UUID4 = Field(
        ...,
        description="A unique identifier for the document.",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    content_type: Optional[str] = Field(
        "application/pdf",
        description="Content type for the file.",
        examples=["application/pdf"],
    )


class PresignedUrlErrorResponse(BaseModel):
    """Pydantic model for error responses when generating presigned URLs.

    Attributes:
        error: The error message describing the issue.
    """

    model_config = ConfigDict(populate_by_name=True)

    error: str = Field(..., description="Error message describing the issue.")
