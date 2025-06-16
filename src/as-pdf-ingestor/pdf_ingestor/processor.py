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
from core.aws import S3Client
from core.utils.config import (
    DOCUMENTS_BUCKET_NAME,
    VECTOR_STORE_BUCKET_NAME,
    BEDROCK_EMBEDDING_MODEL_ID,
)
from pdf_ingestor.aws import BedrockRuntimeClient

# Initialize logger
logger = Logger(service="pdf-ingestor-processor-bedrock")


def extract_srd_info(object_key: str) -> Tuple[str, str, str]:
    """Extract the SRD ID and filename from the S3 object key.

    The S3 object key is expected to be in the format:
    `<owner_id>/<srd_id>/<filename>`, where `<owner_id>` is the owner of the
    SRD, `<srd_id>` is the ID of the SRD, and `<filename>` is the name of
    the file.

    Parameters
    ----------
    object_key : str
        The S3 object key to extract the SRD ID and filename from.

    Returns
    -------
    Tuple[str, str, str]
        A tuple containing the owner ID, SRD ID, and the filename.
    """
    # Split the object key into parts to extract owner ID, SRD ID, and filename
    parts = object_key.split("/", 2)

    if len(parts) < 3:
        raise ValueError(
            f"Invalid S3 object key format: {object_key}. "
            "Expected format is '<owner_id>/<srd_id>/<filename>'."
        )

    return parts[0], parts[1], parts[2]


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
    owner_id, srd_id, filename = extract_srd_info(object_key=object_key)

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

    # Validate the bucket name and object key
    base_file_name = os.path.basename(filename)
    safe_base_file_name = "".join(
        c if c.isalnum() or c in [".", "-"] else "_" for c in base_file_name
    )
    temp_pdf_path = f"/tmp/{safe_base_file_name}"
    temp_faiss_index_name = f"{owner_id}_{srd_id}_faiss_index"
    temp_faiss_index_path = f"/tmp/{temp_faiss_index_name}"

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
            return

        # Split the document into manageable text chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        texts = text_splitter.split_documents(documents)
        lambda_logger.info(f"Split into {len(texts)} text chunks.")
        if not texts:
            lambda_logger.warning(f"No text chunks generated: {object_key}.")
            return

        # Generate embeddings for the text chunks using Bedrock
        lambda_logger.info(
            "Generating embeddings with Bedrock and creating FAISS index..."
        )
        vector_store = FAISS.from_documents(texts, embedding_model)
        lambda_logger.info("FAISS index created successfully in memory.")

        # Save the FAISS index to a temporary directory
        if os.path.exists(temp_faiss_index_path):
            shutil.rmtree(temp_faiss_index_path)
        os.makedirs(temp_faiss_index_path, exist_ok=True)
        vector_store.save_local(folder_path=temp_faiss_index_path)
        lambda_logger.info(
            f"FAISS index saved locally to directory: {temp_faiss_index_path}"
        )

        # Upload the FAISS index files to S3
        s3_index_prefix = f"{owner_id}/{srd_id}/faiss_index"
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
        raise
    except Exception as e:
        lambda_logger.exception(
            f"Unexpected error during processing of {object_key}: {e}"
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

    # Save metadata about the processed document
    metadata = {
        "owner_id": owner_id,
        "srd_id": srd_id,
        "original_filename": filename,
        "chunk_count": len(texts),
        "source_bucket": bucket_name,
        "source_key": decoded_key,
        "vector_index_location": f"{s3_index_prefix}/",
    }

    return metadata
