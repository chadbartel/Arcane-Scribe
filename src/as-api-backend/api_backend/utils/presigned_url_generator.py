# Standard Library
from typing import Optional

# Third Party
from aws_lambda_powertools import Logger

# Local Modules
from core.aws import S3Client
from core.utils.config import DOCUMENTS_BUCKET_NAME

# Initialize logger
logger = Logger(service="presigned-url-generator")


def generate_presigned_url(
    file_name: str,
    srd_id: str,
    owner_id: str,
    document_id: str,
    expiration: Optional[int] = 3600,
    content_type: Optional[str] = "application/pdf",
    metadata: Optional[dict] = None,
) -> str:
    """
    Generate a presigned URL for uploading a file to S3.

    Parameters
    ----------
    file_name : str
        The name of the file to be uploaded.
    srd_id : str
        The client-specified SRD identifier.
    owner_id : str
        The Cognito username of the owner of the document.
    document_id : str
        The unique identifier for the document, used to construct the S3 object
        key.
    expiration : Optional[int], optional
        The expiration time for the presigned URL in seconds, defaults to 3600
        seconds (1 hour).
    content_type : Optional[str], optional
        The content type of the file to be uploaded, defaults to
        "application/pdf".
    metadata : Optional[dict], optional
        Additional metadata to be included with the file upload, defaults to
        None.

    Returns
    -------
    str
        A presigned URL for uploading the file to S3.

    Raises
    ------
    ClientError
        If there is an error generating the presigned URL.
    """
    # Construct object key using SRD ID as prefix
    object_key = f"{owner_id}/{srd_id}/{document_id}/{file_name}"

    # Initialize S3 client
    s3_client = S3Client(bucket_name=DOCUMENTS_BUCKET_NAME)

    # Generate presigned URL with content type
    try:
        presigned_url = s3_client.generate_presigned_upload_url(
            object_key=object_key,
            expiration=expiration,
            content_type=content_type,
            metadata=metadata,
        )

        if not presigned_url:
            raise ValueError("Failed to generate presigned URL.")
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise e
    else:
        logger.info(
            f"Presigned URL generated successfully for {object_key} with "
            f"expiration {expiration} seconds."
        )
        return presigned_url
