"""Unit tests for the processor module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError

# Local Modules
from pdf_ingestor import processor


class TestExtractPathInfo:
    """Test cases for the extract_path_info function."""

    def test_extract_path_info_valid_path(self):
        """Test extraction with a valid S3 object key."""
        object_key = "user123/campaign456/doc789/example.pdf"
        result = processor.extract_path_info(object_key)

        expected = ("user123", "campaign456", "doc789", "example.pdf")
        assert result == expected

    def test_extract_path_info_nested_filename(self):
        """Test extraction with nested folder structure in filename."""
        object_key = "user123/campaign456/doc789/subfolder/example.pdf"
        result = processor.extract_path_info(object_key)

        expected = (
            "user123",
            "campaign456",
            "doc789",
            "subfolder/example.pdf",
        )
        assert result == expected

    def test_extract_path_info_complex_ids(self):
        """Test extraction with complex owner/campaign/document IDs."""
        object_key = (
            "user-with-dashes/campaign_with_underscores/doc@123/file.pdf"
        )
        result = processor.extract_path_info(object_key)

        expected = (
            "user-with-dashes",
            "campaign_with_underscores",
            "doc@123",
            "file.pdf",
        )
        assert result == expected

    def test_extract_path_info_invalid_path_too_few_parts(self):
        """Test extraction with insufficient path components."""
        object_key = "user123/campaign456"

        with pytest.raises(ValueError, match="Invalid S3 object key format"):
            processor.extract_path_info(object_key)

    def test_extract_path_info_invalid_path_empty(self):
        """Test extraction with empty path."""
        object_key = ""

        with pytest.raises(ValueError, match="Invalid S3 object key format"):
            processor.extract_path_info(object_key)

    def test_extract_path_info_single_part(self):
        """Test extraction with single path component."""
        object_key = "justfilename.pdf"

        with pytest.raises(ValueError, match="Invalid S3 object key format"):
            processor.extract_path_info(object_key)

    def test_extract_path_info_three_parts(self):
        """Test extraction with only three path components."""
        object_key = "user123/campaign456/doc789"

        with pytest.raises(ValueError, match="Invalid S3 object key format"):
            processor.extract_path_info(object_key)


class TestProcessS3Object:
    """Test cases for the process_s3_object function."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.bucket_name = "test-bucket"
        self.object_key = "user123/campaign456/doc789/test.pdf"
        self.mock_logger = MagicMock()

    @patch("pdf_ingestor.processor.DatabaseService")
    @patch("pdf_ingestor.processor.S3Client")
    @patch("pdf_ingestor.processor.BedrockRuntimeClient")
    @patch("pdf_ingestor.processor.PyPDFLoader")
    @patch("pdf_ingestor.processor.RecursiveCharacterTextSplitter")
    @patch("pdf_ingestor.processor.FAISS")
    @patch("pdf_ingestor.processor.os")
    @patch("pdf_ingestor.processor.shutil")
    @patch("pdf_ingestor.processor.urllib.parse.unquote_plus")
    def test_process_s3_object_success(
        self,
        mock_unquote_plus,
        mock_shutil,
        mock_os,
        mock_faiss,
        mock_text_splitter_class,
        mock_pdf_loader_class,
        mock_bedrock_client_class,
        mock_s3_client_class,
        mock_db_service_class,
    ):
        """Test successful processing of an S3 object."""
        # Setup mocks
        mock_unquote_plus.return_value = self.object_key
        mock_os.path.basename.return_value = "test.pdf"
        mock_os.path.exists.return_value = True
        mock_os.listdir.return_value = ["doc789.faiss", "doc789.pkl"]
        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs.return_value = None
        mock_os.remove.return_value = None

        # Mock database service
        mock_db_service = MagicMock()
        mock_db_service_class.return_value = mock_db_service

        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        # Mock Bedrock client and embedding model
        mock_bedrock_client = MagicMock()
        mock_embedding_model = MagicMock()
        mock_bedrock_client.get_embedding_model.return_value = (
            mock_embedding_model
        )
        mock_bedrock_client_class.return_value = mock_bedrock_client

        # Mock PDF loader and documents
        mock_pdf_loader = MagicMock()
        mock_documents = [MagicMock(), MagicMock()]
        mock_pdf_loader.load.return_value = mock_documents
        mock_pdf_loader_class.return_value = mock_pdf_loader

        # Mock text splitter and text chunks
        mock_text_splitter = MagicMock()
        mock_texts = [MagicMock(), MagicMock(), MagicMock()]
        mock_text_splitter.split_documents.return_value = mock_texts
        mock_text_splitter_class.return_value = mock_text_splitter

        # Mock FAISS vector store
        mock_vector_store = MagicMock()
        mock_faiss.from_documents.return_value = mock_vector_store

        # Execute the function
        result = processor.process_s3_object(
            bucket_name=self.bucket_name,
            object_key=self.object_key,
            lambda_logger=self.mock_logger,
        )

        # Verify the result
        expected_metadata = {
            "owner_id": "user123",
            "srd_id": "campaign456",
            "document_id": "doc789",
            "original_filename": "test.pdf",
            "chunk_count": 3,
            "source_bucket": self.bucket_name,
            "source_key": self.object_key,
            "vector_index_location": "user123/campaign456/vector_store/",
        }
        assert result == expected_metadata

        # Verify database service calls
        mock_db_service_class.assert_called_once_with(
            table_name=processor.DOCUMENTS_METADATA_TABLE_NAME
        )
        assert mock_db_service.update_document_record.call_count == 2

        # Verify S3 client operations
        mock_s3_client.download_file.assert_called_once_with(
            object_key=self.object_key, download_path="/tmp/test.pdf"
        )
        assert mock_s3_client.upload_file.call_count == 2

        # Verify PDF processing
        mock_pdf_loader_class.assert_called_once_with("/tmp/test.pdf")
        mock_pdf_loader.load.assert_called_once()

        # Verify text splitting
        mock_text_splitter_class.assert_called_once_with(
            chunk_size=1000, chunk_overlap=200
        )
        mock_text_splitter.split_documents.assert_called_once_with(
            mock_documents
        )

        # Verify FAISS operations
        mock_faiss.from_documents.assert_called_once_with(
            mock_texts, mock_embedding_model
        )
        mock_vector_store.save_local.assert_called_once_with(
            folder_path="/tmp/doc789", index_name="doc789"
        )

    @patch("pdf_ingestor.processor.DatabaseService")
    @patch("pdf_ingestor.processor.S3Client")
    @patch("pdf_ingestor.processor.BedrockRuntimeClient")
    @patch("pdf_ingestor.processor.PyPDFLoader")
    @patch("pdf_ingestor.processor.os")
    @patch("pdf_ingestor.processor.urllib.parse.unquote_plus")
    def test_process_s3_object_no_documents_loaded(
        self,
        mock_unquote_plus,
        mock_os,
        mock_pdf_loader_class,
        mock_bedrock_client_class,
        mock_s3_client_class,
        mock_db_service_class,
    ):
        """Test handling when no documents are loaded from PDF."""
        # Setup mocks
        mock_unquote_plus.return_value = self.object_key
        mock_os.path.basename.return_value = "test.pdf"
        mock_os.path.exists.return_value = True
        mock_os.remove.return_value = None

        # Mock database service
        mock_db_service = MagicMock()
        mock_db_service_class.return_value = mock_db_service

        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        # Mock Bedrock client
        mock_bedrock_client = MagicMock()
        mock_bedrock_client_class.return_value = mock_bedrock_client

        # Mock PDF loader with no documents
        mock_pdf_loader = MagicMock()
        mock_pdf_loader.load.return_value = []
        mock_pdf_loader_class.return_value = mock_pdf_loader

        # Execute the function
        result = processor.process_s3_object(
            bucket_name=self.bucket_name,
            object_key=self.object_key,
            lambda_logger=self.mock_logger,
        )

        # Verify the result is None
        assert result is None

        # Verify database service was called to mark as failed
        update_calls = mock_db_service.update_document_record.call_args_list
        assert len(update_calls) == 2

        # First call should set status to 'processing'
        first_call = update_calls[0]
        assert first_call[1]["update_map"]["processing_status"] == "processing"

        # Second call should set status to 'failed'
        second_call = update_calls[1]
        assert second_call[1]["update_map"]["processing_status"] == "failed"

    @patch("pdf_ingestor.processor.DatabaseService")
    @patch("pdf_ingestor.processor.S3Client")
    @patch("pdf_ingestor.processor.BedrockRuntimeClient")
    @patch("pdf_ingestor.processor.PyPDFLoader")
    @patch("pdf_ingestor.processor.RecursiveCharacterTextSplitter")
    @patch("pdf_ingestor.processor.os")
    @patch("pdf_ingestor.processor.urllib.parse.unquote_plus")
    def test_process_s3_object_no_text_chunks(
        self,
        mock_unquote_plus,
        mock_os,
        mock_text_splitter_class,
        mock_pdf_loader_class,
        mock_bedrock_client_class,
        mock_s3_client_class,
        mock_db_service_class,
    ):
        """Test handling when no text chunks are generated."""
        # Setup mocks
        mock_unquote_plus.return_value = self.object_key
        mock_os.path.basename.return_value = "test.pdf"
        mock_os.path.exists.return_value = True
        mock_os.remove.return_value = None

        # Mock database service
        mock_db_service = MagicMock()
        mock_db_service_class.return_value = mock_db_service

        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        # Mock Bedrock client
        mock_bedrock_client = MagicMock()
        mock_bedrock_client_class.return_value = mock_bedrock_client

        # Mock PDF loader with documents
        mock_pdf_loader = MagicMock()
        mock_documents = [MagicMock()]
        mock_pdf_loader.load.return_value = mock_documents
        mock_pdf_loader_class.return_value = mock_pdf_loader

        # Mock text splitter with no chunks
        mock_text_splitter = MagicMock()
        mock_text_splitter.split_documents.return_value = []
        mock_text_splitter_class.return_value = mock_text_splitter

        # Execute the function
        result = processor.process_s3_object(
            bucket_name=self.bucket_name,
            object_key=self.object_key,
            lambda_logger=self.mock_logger,
        )

        # Verify the result is None
        assert result is None

        # Verify database service was called to mark as failed
        update_calls = mock_db_service.update_document_record.call_args_list
        assert len(update_calls) == 2

        # Second call should set status to 'failed'
        second_call = update_calls[1]
        assert second_call[1]["update_map"]["processing_status"] == "failed"

    @patch("pdf_ingestor.processor.DatabaseService")
    @patch("pdf_ingestor.processor.S3Client")
    @patch("pdf_ingestor.processor.BedrockRuntimeClient")
    @patch("pdf_ingestor.processor.os")
    @patch("pdf_ingestor.processor.urllib.parse.unquote_plus")
    def test_process_s3_object_client_error(
        self,
        mock_unquote_plus,
        mock_os,
        mock_bedrock_client_class,
        mock_s3_client_class,
        mock_db_service_class,
    ):
        """Test handling of AWS ClientError during processing."""
        # Setup mocks
        mock_unquote_plus.return_value = self.object_key
        mock_os.path.basename.return_value = "test.pdf"
        mock_os.path.exists.return_value = True
        mock_os.remove.return_value = None

        # Mock database service
        mock_db_service = MagicMock()
        mock_db_service_class.return_value = mock_db_service

        # Mock S3 client to raise ClientError
        mock_s3_client = MagicMock()
        mock_s3_client.download_file.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
            "GetObject",
        )
        mock_s3_client_class.return_value = mock_s3_client

        # Mock Bedrock client
        mock_bedrock_client = MagicMock()
        mock_bedrock_client_class.return_value = mock_bedrock_client

        # Execute the function and verify exception is raised
        with pytest.raises(ClientError):
            processor.process_s3_object(
                bucket_name=self.bucket_name,
                object_key=self.object_key,
                lambda_logger=self.mock_logger,
            )

        # Verify database service was called to mark as failed
        update_calls = mock_db_service.update_document_record.call_args_list
        assert len(update_calls) == 2

        # Second call should set status to 'failed'
        second_call = update_calls[1]
        assert second_call[1]["update_map"]["processing_status"] == "failed"

    @patch("pdf_ingestor.processor.DatabaseService")
    @patch("pdf_ingestor.processor.S3Client")
    @patch("pdf_ingestor.processor.BedrockRuntimeClient")
    @patch("pdf_ingestor.processor.os")
    @patch("pdf_ingestor.processor.urllib.parse.unquote_plus")
    def test_process_s3_object_unexpected_error(
        self,
        mock_unquote_plus,
        mock_os,
        mock_bedrock_client_class,
        mock_s3_client_class,
        mock_db_service_class,
    ):
        """Test handling of unexpected errors during processing."""
        # Setup mocks
        mock_unquote_plus.return_value = self.object_key
        mock_os.path.basename.return_value = "test.pdf"
        mock_os.path.exists.return_value = True
        mock_os.remove.return_value = None

        # Mock database service
        mock_db_service = MagicMock()
        mock_db_service_class.return_value = mock_db_service

        # Mock S3 client to raise unexpected error
        mock_s3_client = MagicMock()
        mock_s3_client.download_file.side_effect = ValueError(
            "Unexpected error"
        )
        mock_s3_client_class.return_value = mock_s3_client

        # Mock Bedrock client
        mock_bedrock_client = MagicMock()
        mock_bedrock_client_class.return_value = mock_bedrock_client  # Execute the function and verify exception is raised
        with pytest.raises(ValueError, match="Unexpected error"):
            processor.process_s3_object(
                bucket_name=self.bucket_name,
                object_key=self.object_key,
                lambda_logger=self.mock_logger,
            )

        # Verify database service was called to mark as failed
        update_calls = mock_db_service.update_document_record.call_args_list
        assert len(update_calls) == 2

        # Second call should set status to 'failed'
        second_call = update_calls[1]
        assert second_call[1]["update_map"]["processing_status"] == "failed"

    @patch("pdf_ingestor.processor.DatabaseService")
    @patch("pdf_ingestor.processor.S3Client")
    @patch("pdf_ingestor.processor.BedrockRuntimeClient")
    @patch("pdf_ingestor.processor.PyPDFLoader")
    @patch("pdf_ingestor.processor.RecursiveCharacterTextSplitter")
    @patch("pdf_ingestor.processor.FAISS")
    @patch("pdf_ingestor.processor.os")
    @patch("pdf_ingestor.processor.shutil")
    @patch("pdf_ingestor.processor.urllib.parse.unquote_plus")
    def test_process_s3_object_cleanup_errors(
        self,
        mock_unquote_plus,
        mock_shutil,
        mock_os,
        mock_faiss,
        mock_text_splitter_class,
        mock_pdf_loader_class,
        mock_bedrock_client_class,
        mock_s3_client_class,
        mock_db_service_class,
    ):
        """Test handling of cleanup errors in finally block."""  # Setup mocks
        mock_unquote_plus.return_value = self.object_key
        mock_os.path.basename.return_value = "test.pdf"

        # Mock os.path.exists to return True for cleanup paths in finally block
        def mock_exists_side_effect(path):
            if path == "/tmp/doc789":  # temp_faiss_index_path
                return True  # Return True for finally cleanup too
            elif path == "/tmp/test.pdf":  # temp_pdf_path
                return True  # For finally cleanup
            return False

        mock_os.path.exists.side_effect = mock_exists_side_effect
        mock_os.listdir.return_value = ["doc789.faiss", "doc789.pkl"]
        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs.return_value = None

        # Mock cleanup errors for finally block calls
        mock_os.remove.side_effect = OSError(
            "File removal error"
        )  # Mock rmtree to work normally first, then fail in finally
        call_count = {"rmtree": 0}

        def mock_rmtree_side_effect(*args):
            call_count["rmtree"] += 1
            if call_count["rmtree"] > 1:  # After first successful call
                raise OSError("Directory removal error")

        mock_shutil.rmtree.side_effect = mock_rmtree_side_effect

        # Mock all other services
        mock_db_service = MagicMock()
        mock_db_service_class.return_value = mock_db_service
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client
        mock_bedrock_client = MagicMock()
        mock_embedding_model = MagicMock()
        mock_bedrock_client.get_embedding_model.return_value = (
            mock_embedding_model
        )
        mock_bedrock_client_class.return_value = mock_bedrock_client
        mock_pdf_loader = MagicMock()
        mock_documents = [MagicMock()]
        mock_pdf_loader.load.return_value = mock_documents
        mock_pdf_loader_class.return_value = mock_pdf_loader
        mock_text_splitter = MagicMock()
        mock_texts = [MagicMock()]
        mock_text_splitter.split_documents.return_value = mock_texts
        mock_text_splitter_class.return_value = mock_text_splitter
        mock_vector_store = MagicMock()
        mock_faiss.from_documents.return_value = mock_vector_store

        # Execute the function - should complete successfully despite cleanup errors
        result = processor.process_s3_object(
            bucket_name=self.bucket_name,
            object_key=self.object_key,
            lambda_logger=self.mock_logger,
        )

        # Verify the result is still returned
        assert result is not None
        assert result["owner_id"] == "user123"

        # Verify cleanup errors were logged
        error_log_calls = [
            call
            for call in self.mock_logger.error.call_args_list
            if "Error cleaning" in str(call)
        ]
        assert len(error_log_calls) == 2

    @patch("pdf_ingestor.processor.extract_path_info")
    def test_process_s3_object_invalid_object_key(
        self, mock_extract_path_info
    ):
        """Test handling of invalid object key format."""
        # Mock extract_path_info to raise ValueError
        mock_extract_path_info.side_effect = ValueError(
            "Invalid S3 object key format"
        )

        # Execute the function and verify exception is raised
        with pytest.raises(ValueError, match="Invalid S3 object key format"):
            processor.process_s3_object(
                bucket_name=self.bucket_name,
                object_key="invalid/key",
                lambda_logger=self.mock_logger,
            )
