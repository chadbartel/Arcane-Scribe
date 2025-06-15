# Standard Library
from typing import Union, Annotated

# Third Party
from fastapi import APIRouter, status, Body, Header
from fastapi.responses import JSONResponse
from aws_lambda_powertools import Logger

# Local Modules
from api_backend.utils import (
    generate_presigned_url,
    AllowedMethod,
    extract_username_from_basic_auth,
)
from api_backend.models import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    PresignedUrlErrorResponse,
)
from api_backend.utils.config import DOCUMENTS_BUCKET_NAME

# Initialize logger
logger = Logger(service="srd")

# Initialize router for asset management
router = APIRouter(prefix="/srd", tags=["SRD"])


@router.post(
    "/upload-url",
    response_model=Union[PresignedUrlResponse, PresignedUrlErrorResponse],
    status_code=status.HTTP_200_OK,
)
def get_presigned_upload_url(
    x_arcane_auth_token: Annotated[str, Header(...)],
    request: PresignedUrlRequest = Body(...),
) -> JSONResponse:
    """Generate a presigned URL for uploading a file to S3.

    **Parameters:**
    - **x_arcane_auth_token**: str
        The authentication token for the request, typically provided in the
    - **request**: PresignedUrlRequest
        The request body containing the file name and SRD ID, including:
        - `file_name`: The name of the file to upload.
        - `srd_id`: The ID of the SRD document.
        - `content_type` (optional): Content type for the file.

    **Returns:**
    - **JSONResponse**: A JSON response containing the presigned URL and other
    details, or an error message if the request fails.
    """
    # Extract username from Basic Auth header
    owner_id = extract_username_from_basic_auth(x_arcane_auth_token)

    # Validate the owner_id
    if not owner_id:
        logger.error(
            "Invalid or missing authentication token",
            extra={"raw_body": request.model_dump_json()},
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid or missing authentication token"},
        )

    # Parse the request body
    try:
        file_name = str(request.file_name).strip()
        srd_id = request.srd_id.strip()
        content_type = (
            request.content_type.strip()
            if request.content_type
            else "application/pdf"
        )
    except Exception as e:
        logger.exception(
            f"Error processing request input: {e}",
            extra={"raw_body": request.model_dump_json()},
        )
        status_code = status.HTTP_400_BAD_REQUEST
        content = {"error": f"Error processing request data: {e}"}

    # Generate the presigned URL
    expiration_seconds = 900  # 15 minutes
    try:
        logger.info(
            f"Generating presigned URL for bucket: {DOCUMENTS_BUCKET_NAME}, key: {file_name}"
        )
        presigned_url = generate_presigned_url(
            file_name=file_name,
            srd_id=srd_id,
            owner_id=owner_id,
            expiration=expiration_seconds,
            content_type=content_type,
        )
        logger.info(
            f"Successfully generated presigned URL for key: {file_name}"
        )
        status_code = status.HTTP_200_OK
        content = {
            "presigned_url": presigned_url,
            "bucket_name": DOCUMENTS_BUCKET_NAME,
            "key": file_name,
            "expires_in": expiration_seconds,
            "method": AllowedMethod.put.value,
            "content_type": content_type,
        }
    except Exception as e:
        logger.exception(
            f"Unexpected error generating presigned URL for key {file_name}: {e}"
        )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": f"Could not generate upload URL: {e}"}

    # Return the response
    return JSONResponse(
        status_code=status_code,
        content=content,
    )
