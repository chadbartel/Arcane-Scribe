# Standard Library
import os
import shutil
import urllib.parse
from typing import Tuple, Dict, Any, Optional

# Third Party
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# Local Modules
from core.aws import S3Client, BedrockRuntimeClient
from core.utils import DocumentProcessingStatus
from core.services import DatabaseService
from core.utils.config import (
    DOCUMENTS_BUCKET_NAME,
    VECTOR_STORE_BUCKET_NAME,
    BEDROCK_EMBEDDING_MODEL_ID,
    DOCUMENTS_METADATA_TABLE_NAME,
)

# Initialize logger
logger = Logger(service="pdf-ingestor-processor-bedrock")


def extract_path_info(object_key: str) -> Tuple[str, str, str, str]:
    """Extracts the owner ID, SRD ID, document ID, and filename from an S3
    object key.

    The S3 object key is expected to be in the format:
    `<owner_id>/<srd_id>/<document_id>/<filename>`, where:
    - `<owner_id>` is the Cognito username of the document owner.
    - `<srd_id>` is the client-specified SRD identifier.
    - `<document_id>` is the unique identifier for the document.
    - `<filename>` is the name of the file being processed.

    Parameters
    ----------
    object_key : str
        The S3 object key from which to extract the information.

    Returns
    -------
    Tuple[str, str, str, str]
        A tuple containing the owner ID, SRD ID, document ID, and filename.
    """
    # Split the object key into parts
    parts = object_key.split("/", 3)

    # Ensure there are enough parts to extract the required information
    if len(parts) < 4:
        raise ValueError(
            f"Invalid S3 object key format: {object_key}. "
            "Expected format is '<owner_id>/<srd_id>/<document_id>/<filename>'."
        )

    return parts[0], parts[1], parts[2], parts[3]


def process_s3_object(
    bucket_name: str, object_key: str, lambda_logger: Logger
) -> Optional[Dict[str, Any]]:
    """Process a PDF file from S3, generate embeddings using Bedrock,
    and create a FAISS index. The FAISS index is then uploaded back to S3.

    Parameters
    ----------
    bucket_name : str
        The name of the S3 bucket containing the PDF file.
    object_key : str
        The key of the PDF file in the S3 bucket.
    lambda_logger : Logger
        The logger instance for logging messages.

    Returns
    -------
    Optional[Dict[str, Any]]
        A dictionary containing metadata about the processed document,
        including the owner ID, SRD ID, original filename, chunk count,
        source bucket, source key, and vector index location in S3. If no
        documents are loaded or no text chunks are generated, returns None.

    Raises
    -------
    RuntimeError
        If the S3 client, Bedrock client, or embedding model is not initialized.
    EnvironmentError
        If the VECTOR_STORE_BUCKET_NAME environment variable is not set.
    ClientError
        If there is an error interacting with AWS services.
    Exception
        For any other unexpected errors during processing.
    """
    # Extract SRD ID form object key
    owner_id, srd_id, document_id, filename = extract_path_info(
        object_key=object_key
    )

    # Initialize database service
    db_service = DatabaseService(table_name=DOCUMENTS_METADATA_TABLE_NAME)

    # Update the document metadata in the database to 'processing'
    db_service.update_document_record(
        owner_id=owner_id,
        srd_id=srd_id,
        document_id=document_id,
        update_map={
            "processing_status": DocumentProcessingStatus.processing.value,
        },
    )

    # Initialize the S3 client
    s3_client = S3Client(bucket_name=DOCUMENTS_BUCKET_NAME)

    # Initialize the Bedrock runtime client
    bedrock_runtime_client = BedrockRuntimeClient()

    # Get the embedding model
    embedding_model = bedrock_runtime_client.get_embedding_model(
        model_id=BEDROCK_EMBEDDING_MODEL_ID
    )

    # Decode object key to handle any URL encoding
    decoded_key = urllib.parse.unquote_plus(object_key)

    # Define a unique temporary path for the FAISS index using the document_id
    temp_pdf_path = f"/tmp/{os.path.basename(filename)}"
    temp_faiss_index_path = (
        f"/tmp/{document_id}"  # Use document_id for the temp folder name
    )

    try:
        # Download the PDF file from S3
        lambda_logger.info(
            f"Downloading s3://{bucket_name}/{object_key} to {temp_pdf_path}"
        )
        s3_client.download_file(
            object_key=decoded_key, download_path=temp_pdf_path
        )
        lambda_logger.info(f"Successfully downloaded PDF to {temp_pdf_path}")

        # Load the PDF document using PyPDFLoader
        lambda_logger.info(
            f"Loading PDF document from {temp_pdf_path} using PyPDFLoader."
        )
        loader = PyPDFLoader(temp_pdf_path)
        documents = loader.load()
        lambda_logger.info(
            f"Loaded {len(documents)} document pages/sections from PDF."
        )
        if not documents:
            lambda_logger.warning(
                f"No documents loaded from PDF: {object_key}."
            )

            # Update the document metadata in the database to 'failed'
            db_service.update_document_record(
                owner_id=owner_id,
                srd_id=srd_id,
                document_id=document_id,
                update_map={
                    "processing_status": DocumentProcessingStatus.failed.value,
                },
            )

            return

        # Split the document into manageable text chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        texts = text_splitter.split_documents(documents)
        lambda_logger.info(f"Split into {len(texts)} text chunks.")
        if not texts:
            lambda_logger.warning(f"No text chunks generated: {object_key}.")

            # Update the document metadata in the database to 'failed'
            db_service.update_document_record(
                owner_id=owner_id,
                srd_id=srd_id,
                document_id=document_id,
                update_map={
                    "processing_status": DocumentProcessingStatus.failed.value,
                },
            )

            return

        # Add source and page number to metadata of each text chunk
        for _, text in enumerate(texts):
            # PyPDFLoader adds a 'page' key automatically
            text.metadata["source"] = filename  # The PDF file path in S3

        # Generate embeddings for the text chunks using Bedrock
        lambda_logger.info(
            "Generating embeddings with Bedrock and creating FAISS index..."
        )
        vector_store = FAISS.from_documents(texts, embedding_model)
        lambda_logger.info("FAISS index created successfully in memory.")

        # Clean up any old temporary directories if they exist
        if os.path.exists(temp_faiss_index_path):
            shutil.rmtree(temp_faiss_index_path)
        os.makedirs(temp_faiss_index_path, exist_ok=True)

        # Save the FAISS index locally using the document_id as the index_name
        vector_store.save_local(
            folder_path=temp_faiss_index_path,
            index_name=document_id,
        )
        lambda_logger.info(
            f"FAISS index saved locally to directory: {temp_faiss_index_path}"
        )

        # Define a more specific S3 prefix for the vector store
        s3_index_prefix = f"{owner_id}/{srd_id}/vector_store"

        # Upload the FAISS index files to S3
        for file_name_in_index_dir in os.listdir(temp_faiss_index_path):
            local_file_to_upload = os.path.join(
                temp_faiss_index_path, file_name_in_index_dir
            )
            s3_target_key = f"{s3_index_prefix}/{file_name_in_index_dir}"

            lambda_logger.info(
                f"Uploading {local_file_to_upload} to s3://{VECTOR_STORE_BUCKET_NAME}/{s3_target_key}"
            )
            s3_client.upload_file(
                file_path=local_file_to_upload,
                object_key=s3_target_key,
                bucket_name=VECTOR_STORE_BUCKET_NAME,
            )
        lambda_logger.info(
            f"FAISS index for {object_key} uploaded to S3: {VECTOR_STORE_BUCKET_NAME}/{s3_index_prefix}"
        )

    # Handle specific AWS errors and log them
    except ClientError as e:
        lambda_logger.exception(
            f"AWS ClientError during processing of {object_key}: {e}"
        )
        # Update the document metadata in the database to 'failed'
        db_service.update_document_record(
            owner_id=owner_id,
            srd_id=srd_id,
            document_id=document_id,
            update_map={
                "processing_status": DocumentProcessingStatus.failed.value,
            },
        )
        raise
    except Exception as e:
        lambda_logger.exception(
            f"Unexpected error during processing of {object_key}: {e}"
        )
        # Update the document metadata in the database to 'failed'
        db_service.update_document_record(
            owner_id=owner_id,
            srd_id=srd_id,
            document_id=document_id,
            update_map={
                "processing_status": DocumentProcessingStatus.failed.value,
            },
        )
        raise
    finally:
        # Clean up temporary files and directories
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception as e_clean:
                lambda_logger.error(
                    f"Error cleaning temp PDF {temp_pdf_path}: {e_clean}"
                )
        # Clean up the FAISS index directory
        if os.path.exists(temp_faiss_index_path):
            try:
                shutil.rmtree(temp_faiss_index_path)
            except Exception as e_clean:
                lambda_logger.error(
                    f"Error cleaning temp FAISS dir {temp_faiss_index_path}: {e_clean}"
                )

    # Update the document metadata in the database to 'completed'
    db_service.update_document_record(
        owner_id=owner_id,
        srd_id=srd_id,
        document_id=document_id,
        update_map={
            "processing_status": DocumentProcessingStatus.completed.value,
        },
    )

    # Save metadata about the processed document
    metadata = {
        "owner_id": owner_id,
        "srd_id": srd_id,
        "document_id": document_id,
        "original_filename": filename,
        "chunk_count": len(texts),
        "source_bucket": bucket_name,
        "source_key": decoded_key,
        "vector_index_location": f"{s3_index_prefix}/",
    }

    return metadata
