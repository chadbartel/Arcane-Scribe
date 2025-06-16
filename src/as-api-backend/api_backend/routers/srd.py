# Standard Library
from uuid import uuid4
from typing import Union, Annotated

# Third Party
from fastapi import APIRouter, status, Body, Header, Path
from fastapi.responses import JSONResponse
from aws_lambda_powertools import Logger

# Local Modules
from core.aws import S3Client
from core.utils import AllowedMethod, extract_username_from_basic_auth
from core.services import DatabaseService
from core.utils.config import (
    DOCUMENTS_BUCKET_NAME,
    DOCUMENTS_METADATA_TABLE_NAME,
)
from api_backend.utils import generate_presigned_url
from api_backend.models import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    PresignedUrlErrorResponse,
)

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
        `x-arcane-auth-token` header.
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

    # Generate a unique document ID
    document_id = str(uuid4())

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
        return JSONResponse(status_code=status_code, content=content)

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
            metadata={"document_id": document_id},
        )
        logger.info(
            f"Successfully generated presigned URL for key: {file_name}"
        )
        status_code = status.HTTP_200_OK
    except Exception as e:
        logger.exception(
            f"Unexpected error generating presigned URL for key {file_name}: {e}"
        )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": f"Could not generate upload URL: {e}"}
        return JSONResponse(status_code=status_code, content=content)

    # Create a metadata record in the database
    s3_key = f"{owner_id}/{srd_id}/{file_name}"
    db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)
    db_service.create_document_record(
        owner_id=owner_id,
        srd_id=srd_id,
        file_name=file_name,
        s3_key=s3_key,
        content_type=content_type,
        document_id=document_id,
    )

    # Construct the response content
    content = {
        "presigned_url": presigned_url,
        "bucket_name": DOCUMENTS_BUCKET_NAME,
        "key": file_name,
        "expires_in": expiration_seconds,
        "method": AllowedMethod.put.value,
        "srd_id": srd_id,
        "document_id": document_id,
        "content_type": content_type,
    }

    # Return the response
    return JSONResponse(
        status_code=status_code,
        content=content,
    )


@router.delete("/{srd_id}/documents/{document_id}")
def delete_document_record(
    x_arcane_auth_token: Annotated[str, Header(...)],
    srd_id: str = Path(..., description="The ID of the SRD document"),
    document_id: str = Path(
        ..., description="The ID of the document to delete"
    ),
) -> JSONResponse:
    """Delete a document record from the database and S3.

    **Parameters:**
    - **x_arcane_auth_token**: str
        The authentication token for the request, typically provided in the
        `x-arcane-auth-token` header.
    - **srd_id**: str
        The ID of the SRD document.
    - **document_id**: str
        The ID of the document to delete.

    **Returns:**
    - **JSONResponse**: A JSON response indicating the success or failure of
    the deletion operation.
    """
    # Initialize the status code and content
    status_code = status.HTTP_200_OK
    content = {"message": "Document deleted successfully"}

    # Extract username from Basic Auth header
    owner_id = extract_username_from_basic_auth(x_arcane_auth_token)

    # Validate the owner_id
    if not owner_id:
        logger.error("Invalid or missing authentication token")
        status_code = status.HTTP_401_UNAUTHORIZED
        content = {"error": "Invalid or missing authentication token"}
        return JSONResponse(status_code=status_code, content=content)

    # Initialize the database service
    db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)

    # Check if the document exists in the database
    logger.info(
        f"Checking if document exists in database: owner_id={owner_id}, "
        f"srd_id={srd_id}, document_id={document_id}"
    )
    document_record = db_service.get_document_record(
        owner_id=owner_id,
        srd_id=srd_id,
        document_id=document_id,
    )
    if not document_record:
        status_code = status.HTTP_404_NOT_FOUND
        content = {"error": "Document not found in database"}
        return JSONResponse(status_code=status_code, content=content)
    logger.info(
        f"Document found in database: {document_record['document_id']}"
    )

    # Delete the document from S3
    try:
        s3_key = document_record["s3_key"]
        logger.info(f"Deleting document from S3: {s3_key}")
        s3_client = S3Client(bucket_name=DOCUMENTS_BUCKET_NAME)
        s3_client.delete_object(object_key=s3_key)
        logger.info(f"Deleted document from S3: {s3_key}")
    except Exception as e:
        logger.exception(f"Error deleting document from S3: {e}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": "Could not delete document from S3"}
        return JSONResponse(status_code=status_code, content=content)

    # Delete the document record from the database
    try:
        logger.info(
            f"Deleting document record from database: owner_id={owner_id}, srd_id={srd_id}, document_id={document_id}"
        )
        db_service.delete_document_record(
            owner_id=owner_id,
            srd_id=srd_id,
            document_id=document_id,
        )
    except Exception as e:
        logger.exception(f"Error deleting document record from database: {e}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": "Could not delete document record from database"}
        return JSONResponse(status_code=status_code, content=content)

    return JSONResponse(status_code=status_code, content=content)


@router.get("/{srd_id}/documents", response_model=list)
def list_document_records(
    x_arcane_auth_token: Annotated[str, Header(...)],
    srd_id: str = Path(..., description="The ID of the SRD document"),
) -> JSONResponse:
    """List all document records for a given SRD document.

    **Parameters:**
    - **x_arcane_auth_token**: str
        The authentication token for the request, typically provided in the
        `x-arcane-auth-token` header.
    - **srd_id**: str
        The ID of the SRD document.

    **Returns:**
    - **JSONResponse**: A JSON response containing a list of document records
      or an error message if no records are found.
    """
    # Extract username from Basic Auth header
    owner_id = extract_username_from_basic_auth(x_arcane_auth_token)

    # Validate the owner_id
    if not owner_id:
        logger.error("Invalid or missing authentication token")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid or missing authentication token"},
        )

    # Initialize the database service
    db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)

    # Retrieve the list of document records from the database
    logger.info(
        f"Retrieving document records from database: owner_id={owner_id}, srd_id={srd_id}"
    )
    document_records = db_service.list_document_records(
        owner_id=owner_id,
        srd_id=srd_id,
    )

    if not document_records:
        logger.warning("No document records found in database")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "No documents found"},
        )

    logger.info(f"Document records retrieved successfully: {document_records}")

    return JSONResponse(
        status_code=status.HTTP_200_OK, content=document_records
    )


@router.get("/{srd_id}/documents/{document_id}")
def get_document_record(
    x_arcane_auth_token: Annotated[str, Header(...)],
    srd_id: str = Path(..., description="The ID of the SRD document"),
    document_id: str = Path(..., description="The ID of the document"),
) -> JSONResponse:
    """Retrieve a document record from the database.

    **Parameters:**
    - **x_arcane_auth_token**: str
        The authentication token for the request, typically provided in the
        `x-arcane-auth-token` header.
    - **srd_id**: str
        The ID of the SRD document.
    - **document_id**: str
        The ID of the document to retrieve.

    **Returns:**
    - **JSONResponse**: A JSON response containing the document record or an
      error message if the record does not exist.
    """
    # Extract username from Basic Auth header
    owner_id = extract_username_from_basic_auth(x_arcane_auth_token)

    # Validate the owner_id
    if not owner_id:
        logger.error("Invalid or missing authentication token")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid or missing authentication token"},
        )

    # Initialize the database service
    db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)

    # Retrieve the document record from the database
    logger.info(
        f"Retrieving document record from database: owner_id={owner_id}, "
        f"srd_id={srd_id}, document_id={document_id}"
    )
    document_record = db_service.get_document_record(
        owner_id=owner_id,
        srd_id=srd_id,
        document_id=document_id,
    )

    if not document_record:
        logger.warning("Document record not found in database")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Document not found"},
        )

    logger.info(f"Document record retrieved successfully: {document_record}")

    return JSONResponse(
        status_code=status.HTTP_200_OK, content=document_record
    )
