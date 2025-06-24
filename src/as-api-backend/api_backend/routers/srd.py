# Standard Library
from uuid import uuid4
from typing import Union

# Third Party
from fastapi import APIRouter, status, Body, Path, Depends
from fastapi.responses import JSONResponse
from aws_lambda_powertools import Logger

# Local Modules
from core.aws import S3Client
from core.utils import AllowedMethod
from core.services import DatabaseService
from core.utils.config import (
    DOCUMENTS_BUCKET_NAME,
    DOCUMENTS_METADATA_TABLE_NAME,
    VECTOR_STORE_BUCKET_NAME,
)
from api_backend.models import (
    User,
    PresignedUrlRequest,
    PresignedUrlResponse,
    PresignedUrlErrorResponse,
)
from api_backend.dependencies import get_current_user

# Initialize logger
logger = Logger(service="srd")

# Initialize router for asset management
router = APIRouter(prefix="/srd", tags=["SRD"])

# Initialize S3 clients and database service
db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)
s3_client_docs = S3Client(bucket_name=DOCUMENTS_BUCKET_NAME)
s3_client_vectors = S3Client(bucket_name=VECTOR_STORE_BUCKET_NAME)


@router.get("", status_code=status.HTTP_200_OK, response_model=list)
def list_owner_documents(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """List all SRD documents for the current user.

    **Parameters:**
    - **current_user**: The current authenticated user.

    **Returns:**
    - **JSONResponse**: A JSON response containing a list of SRD IDs or an
        error message if no documents are found.
    """
    # Extract the username
    owner_id = current_user.username

    # Retrieve the list of SRD IDs from the database
    logger.info(f"Retrieving SRD IDs for owner_id={owner_id}")

    # Get list of objects in S3 bucket under user's owner_id
    srd_objects = s3_client_docs.list_objects(prefix=f"{owner_id}/")

    # Check if any SRD objects were found
    if not srd_objects:
        logger.warning("No SRD documents found for the user")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "No SRD documents found"},
        )

    logger.info(
        "SRD documents retrieved successfully",
        extra={"srd_objects": srd_objects},
    )

    # Extract SRD IDs from the S3 object keys and ensure uniqueness
    srd_ids = list(
        set([obj["Key"].split("/")[1] for obj in srd_objects])
    ).sort()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=srd_ids,
    )


@router.post(
    "/{srd_id}/documents/upload-url",
    response_model=Union[PresignedUrlResponse, PresignedUrlErrorResponse],
    status_code=status.HTTP_200_OK,
)
def get_presigned_upload_url(
    srd_id: str = Path(..., description="The ID of the SRD document"),
    current_user: User = Depends(get_current_user),
    request: PresignedUrlRequest = Body(...),
) -> JSONResponse:
    """Generate a presigned URL for uploading a file to S3.

    **Parameters:**
    - **srd_id**: The ID of the SRD document.
    - **request**: The request body containing the file name and content type.

    **Returns:**
    - **JSONResponse**: A JSON response containing the presigned URL and other
    details, or an error message if the request fails.
    """
    # Extract the username
    owner_id = current_user.username

    # Generate a unique document ID
    document_id = str(uuid4())

    # Parse the request body
    try:
        file_name = str(request.file_name).strip()
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
        object_key = f"{owner_id}/{srd_id}/{document_id}/{file_name}"
        logger.info(
            f"Generating presigned URL for s3://{DOCUMENTS_BUCKET_NAME}/{object_key}"
        )
        presigned_url = s3_client_docs.generate_presigned_upload_url(
            object_key=object_key,
            expiration=expiration_seconds,
            content_type=content_type,
            metadata={
                "srd_id": srd_id,
                "document_id": document_id,
                "owner_id": owner_id,
            },
        )
        logger.info(
            f"Successfully generated presigned URL for key: {file_name}"
        )
        status_code = status.HTTP_200_OK

        # Create a metadata record in the database
        logger.info("Creating document record in metadata database")
        db_service.create_document_record(
            owner_id=owner_id,
            srd_id=srd_id,
            file_name=file_name,
            s3_key=object_key,
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

        return JSONResponse(
            status_code=status_code,
            content=content,
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error generating presigned URL for key {file_name}: {e}"
        )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": f"Could not generate upload URL: {e}"}
        return JSONResponse(status_code=status_code, content=content)


@router.delete(
    "/{srd_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_document_record(
    srd_id: str = Path(..., description="The ID of the SRD document"),
    document_id: str = Path(
        ..., description="The ID of the document to delete"
    ),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Delete a document record from the database and S3.

    **Parameters:**
    - **srd_id**: The ID of the SRD document.
    - **document_id**: The ID of the document to delete.

    **Returns:**
    - **JSONResponse**: A JSON response indicating the success or failure of
    the deletion operation.
    """
    # Initialize the status code and content
    status_code = status.HTTP_204_NO_CONTENT

    # Extract the username
    owner_id = current_user.username

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
        "Document found in database",
        extra={"document_id": document_record["document_id"]},
    )

    # Delete the document from documents bucket in S3
    try:
        s3_key = document_record["s3_key"]
        logger.info(f"Deleting document from documents bucket in S3: {s3_key}")
        s3_client_docs.delete_object(object_key=s3_key)
        logger.info(f"Deleted document from documents bucket in S3: {s3_key}")
    except Exception as e:
        logger.exception(f"Error deleting document from S3: {e}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": "Could not delete document from S3"}
        return JSONResponse(status_code=status_code, content=content)

    # Delete the index from the vector store bucket in S3
    try:
        faiss_key = f"{owner_id}/{srd_id}/vector_store/{document_id}.faiss"
        pickle_key = f"{owner_id}/{srd_id}/vector_store/{document_id}.pkl"
        logger.info("Deleting index from vector store bucket in S3")
        s3_client_vectors.delete_object(object_key=faiss_key)
        s3_client_vectors.delete_object(object_key=pickle_key)
        logger.info("Deleted index from vector store bucket in S3")
    except Exception as e:
        logger.exception(f"Error deleting document from S3: {e}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": "Could not delete document from S3"}
        return JSONResponse(status_code=status_code, content=content)

    # Delete the document record from the database
    try:
        logger.info(
            f"Deleting document record from database: owner_id={owner_id}, "
            f"srd_id={srd_id}, document_id={document_id}"
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

    return JSONResponse(status_code=status_code, content=None)


@router.delete("/{srd_id}/documents", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_document_records(
    srd_id: str = Path(..., description="The ID of the SRD document"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Delete all document records for a given SRD document.

    **Parameters:**
    - **srd_id**: The ID of the SRD document.

    **Returns:**
    - **JSONResponse**: A JSON response indicating the success or failure of
      the deletion operation.
    """
    # Extract the username
    owner_id = current_user.username

    # Get all documents for the given owner ID and SRD ID
    logger.info(f"Retrieving all document files for SRD ID {srd_id}")
    document_objects = s3_client_docs.list_objects(
        prefix=f"{owner_id}/{srd_id}/"
    )

    # Delete each document file from S3
    logger.info(f"Deleting all document files for SRD ID {srd_id}")
    for document_object in document_objects:
        document_key = document_object.get("Key")
        if document_key:
            try:
                logger.info(f"Deleting document from S3: {document_key}")
                s3_client_docs.delete_object(object_key=document_key)
                logger.info(f"Deleted document from S3: {document_key}")
            except Exception as e:
                logger.error(
                    f"Error deleting document from S3: {e}",
                    extra={"document_key": document_key},
                )
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Could not delete document from S3"},
                )

    # Get all vector store files for the given owner ID and SRD ID
    vector_store_prefix = f"{owner_id}/{srd_id}/vector_store/"
    logger.info(f"Retrieving all vector store files for SRD ID {srd_id}")
    vector_store_objects = s3_client_vectors.list_objects(
        prefix=vector_store_prefix
    )

    # Delete each vector store file from S3
    logger.info(f"Deleting all vector store files for SRD ID {srd_id}")
    for vector_store_object in vector_store_objects:
        vector_store_key = vector_store_object.get("Key")
        if vector_store_key:
            try:
                logger.info(
                    f"Deleting vector store file from S3: {vector_store_key}"
                )
                s3_client_vectors.delete_object(object_key=vector_store_key)
                logger.info(
                    f"Deleted vector store file from S3: {vector_store_key}"
                )
            except Exception as e:
                logger.error(
                    f"Error deleting vector store file from S3: {e}",
                    extra={"vector_store_key": vector_store_key},
                )
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "Could not delete vector store file from S3"
                    },
                )

    # Delete all document records for the given SRD ID
    try:
        logger.info(f"Deleting all document metadata for SRD ID {srd_id}")
        response = db_service.delete_all_document_records(
            owner_id=owner_id, srd_id=srd_id
        )
        logger.info(
            f"Response after deleting all metadata records for SRD ID "
            f"{srd_id}: {response}"
        )
    except Exception as e:
        logger.exception(f"Error deleting document record from database: {e}")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": "Could not delete document record from database"}
        return JSONResponse(status_code=status_code, content=content)

    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.get(
    "/{srd_id}/documents", status_code=status.HTTP_200_OK, response_model=list
)
def list_document_records(
    srd_id: str = Path(..., description="The ID of the SRD document"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """List all document records for a given SRD document.

    **Parameters:**
    - **srd_id**: The ID of the SRD document.

    **Returns:**
    - **JSONResponse**: A JSON response containing a list of document records
      or an error message if no records are found.
    """
    # Extract the username
    owner_id = current_user.username

    # Retrieve the list of document records from the database
    logger.info(
        f"Retrieving document records from database: owner_id={owner_id}, srd_id={srd_id}"
    )
    document_records = db_service.list_document_records(
        owner_id=owner_id,
        srd_id=srd_id,
    ).get("Items", [])

    # Check if any document records were found
    if not document_records:
        logger.warning("No document records found in database")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "No documents found"},
        )
    logger.info(
        "Document records retrieved successfully",
        extra={"document_records": document_records},
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK, content=document_records
    )


@router.get("/{srd_id}/documents/{document_id}")
def get_document_record(
    srd_id: str = Path(..., description="The ID of the SRD document"),
    document_id: str = Path(..., description="The ID of the document"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """Retrieve a document record from the database.

    **Parameters:**
    - **srd_id**: The ID of the SRD document.
    - **document_id**: The ID of the document to retrieve.

    **Returns:**
    - **JSONResponse**: A JSON response containing the document record or an
      error message if the record does not exist.
    """
    # Extract the username
    owner_id = current_user.username

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

    # Check if any document records were found
    if not document_record:
        logger.warning("Document record not found in database")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Document not found"},
        )
    logger.info(
        "Document record retrieved successfully",
        extra={"document_records": document_record},
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK, content=document_record
    )
