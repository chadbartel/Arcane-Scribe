"""Unit tests for the rag_query_processor module."""

# Standard Library
import hashlib
from unittest.mock import MagicMock, patch, Mock

# Third Party
import pytest
from botocore.exceptions import ClientError

# Local Modules
from core.utils import DocumentProcessingStatus

# Patch AWS clients and services before any imports that use them
with patch(
    "core.aws.BedrockRuntimeClient"
) as mock_bedrock_runtime_client_class:
    with patch("core.services.DatabaseService") as mock_db_service_class:
        with patch("core.aws.S3Client") as mock_s3_client_class:
            with patch("core.aws.DynamoDb") as mock_dynamo_client_class:
                # Set up mock instances
                mock_bedrock_runtime_client_class.return_value = Mock()
                mock_db_service_class.return_value = Mock()
                mock_s3_client_class.return_value = Mock()
                mock_dynamo_client_class.return_value = Mock()

                # Import the module under test after patching
                # Local Modules
                import api_backend.utils.rag_query_processor  # noqa: F401


@pytest.fixture
def mock_bedrock_client():
    """Mock the Bedrock client for testing."""
    with patch(
        "api_backend.utils.rag_query_processor.BEDROCK_RUNTIME_CLIENT"
    ) as mock_client:
        yield mock_client


@pytest.fixture
def mock_db_service_class():
    """Mock the DatabaseService class for testing."""
    with patch(
        "api_backend.utils.rag_query_processor.DatabaseService"
    ) as mock_class:
        yield mock_class


@pytest.fixture
def mock_s3_client_class():
    """Mock the S3Client class for testing."""
    with patch("api_backend.utils.rag_query_processor.S3Client") as mock_class:
        yield mock_class


class TestGetLlmInstance:
    """Test cases for the get_llm_instance function."""

    def test_get_llm_instance_with_valid_config(self, mock_bedrock_client):
        """Test get_llm_instance with valid generation config."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_llm_instance

        # Arrange
        mock_chat_model = MagicMock()
        mock_bedrock_client.get_chat_model.return_value = mock_chat_model

        generation_config = {
            "temperature": 0.5,
            "top_p": 0.8,
            "max_tokens": 2048,
            "stop_sequences": ["Human:", "Assistant:"],
        }

        # Act
        result = get_llm_instance(generation_config)

        # Assert
        assert result == mock_chat_model
        mock_bedrock_client.get_chat_model.assert_called_once()
        call_args = mock_bedrock_client.get_chat_model.call_args
        assert call_args[1]["model_kwargs"]["temperature"] == 0.5
        assert call_args[1]["model_kwargs"]["top_p"] == 0.8
        assert call_args[1]["model_kwargs"]["max_tokens"] == 2048
        assert call_args[1]["model_kwargs"]["stop_sequences"] == [
            "Human:",
            "Assistant:",
        ]

    def test_get_llm_instance_with_defaults(self, mock_bedrock_client):
        """Test get_llm_instance with empty config using defaults."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_llm_instance

        # Arrange
        mock_chat_model = MagicMock()
        mock_bedrock_client.get_chat_model.return_value = mock_chat_model
        generation_config = {}

        # Act
        result = get_llm_instance(generation_config)

        # Assert
        assert result == mock_chat_model
        call_args = mock_bedrock_client.get_chat_model.call_args
        assert call_args[1]["model_kwargs"]["temperature"] == 0.1
        assert call_args[1]["model_kwargs"]["top_p"] == 1.0
        assert call_args[1]["model_kwargs"]["max_tokens"] == 1024
        assert call_args[1]["model_kwargs"]["stop_sequences"] == []

    def test_get_llm_instance_with_none_values(self, mock_bedrock_client):
        """Test get_llm_instance with None values in config."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_llm_instance

        # Arrange
        mock_chat_model = MagicMock()
        mock_bedrock_client.get_chat_model.return_value = mock_chat_model
        generation_config = {
            "temperature": None,
            "top_p": None,
            "max_tokens": None,
            "stop_sequences": None,
        }

        # Act
        result = get_llm_instance(generation_config)

        # Assert
        assert result == mock_chat_model
        call_args = mock_bedrock_client.get_chat_model.call_args
        assert call_args[1]["model_kwargs"]["temperature"] == 0.1
        assert call_args[1]["model_kwargs"]["top_p"] == 1.0
        assert call_args[1]["model_kwargs"]["max_tokens"] == 1024
        assert call_args[1]["model_kwargs"]["stop_sequences"] == []

    def test_get_llm_instance_exception_fallback_to_default(
        self, mock_bedrock_client
    ):
        """Test get_llm_instance falling back to default on exception."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_llm_instance

        # Arrange
        mock_default_model = MagicMock()
        mock_bedrock_client.get_chat_model.side_effect = [
            Exception("First call failed"),
            mock_default_model,  # Second call succeeds (default)
        ]
        generation_config = {"temperature": 0.5}

        # Act
        result = get_llm_instance(generation_config)

        # Assert
        assert result == mock_default_model
        assert mock_bedrock_client.get_chat_model.call_count == 2

    def test_get_llm_instance_type_conversion(self, mock_bedrock_client):
        """Test get_llm_instance converts string values to proper types."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_llm_instance

        # Arrange
        mock_chat_model = MagicMock()
        mock_bedrock_client.get_chat_model.return_value = mock_chat_model
        generation_config = {
            "temperature": "0.7",
            "top_p": "0.9",
            "max_tokens": "1500",
        }

        # Act
        result = get_llm_instance(generation_config)

        # Assert
        assert result == mock_chat_model
        call_args = mock_bedrock_client.get_chat_model.call_args
        assert call_args[1]["model_kwargs"]["temperature"] == 0.7
        assert call_args[1]["model_kwargs"]["top_p"] == 0.9
        assert call_args[1]["model_kwargs"]["max_tokens"] == 1500

    def test_get_llm_instance_both_calls_fail(self, mock_bedrock_client):
        """Test get_llm_instance when both dynamic and default calls fail."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_llm_instance

        # Arrange
        mock_bedrock_client.get_chat_model.side_effect = [
            Exception("First call failed"),
            Exception("Second call also failed"),
        ]
        generation_config = {"temperature": 0.5}

        # Act & Assert
        with pytest.raises(Exception, match="Second call also failed"):
            get_llm_instance(generation_config)


class TestLoadAndMergeFaissIndicesForSrd:
    """Test cases for the _load_and_merge_faiss_indices_for_srd function."""

    def setup_method(self):
        """Setup method to clear cache before each test."""
        # Local Modules
        from api_backend.utils.rag_query_processor import FAISS_INDEX_CACHE

        FAISS_INDEX_CACHE.clear()

    @patch("api_backend.utils.rag_query_processor.os")
    @patch("api_backend.utils.rag_query_processor.shutil")
    @patch("api_backend.utils.rag_query_processor.FAISS")
    @patch("api_backend.utils.rag_query_processor.S3Client")
    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_cache_hit(
        self,
        mock_db_service_class,
        mock_s3_client_class,
        mock_faiss,
        mock_shutil,
        mock_os,
    ):
        """Test cache hit scenario."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            FAISS_INDEX_CACHE,
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        composite_key = f"{owner_id}#{srd_id}"
        mock_logger = MagicMock()

        # Setup cache with existing index
        mock_cached_index = MagicMock()
        FAISS_INDEX_CACHE[composite_key] = mock_cached_index

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result == mock_cached_index
        mock_logger.info.assert_called_with(
            f"FAISS index for '{composite_key}' found in cache."
        )
        # Ensure no external services were called
        mock_db_service_class.assert_not_called()
        mock_s3_client_class.assert_not_called()

    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_no_documents(
        self, mock_db_service_class
    ):
        """Test scenario with no documents found."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {"Items": []}
        mock_db_service_class.return_value = mock_db_service

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result is None
        mock_db_service.list_document_records.assert_called_once_with(
            owner_id=owner_id, srd_id=srd_id
        )

    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_db_exception(
        self, mock_db_service_class
    ):
        """Test database exception handling."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        mock_db_service = MagicMock()
        mock_db_service.list_document_records.side_effect = Exception(
            "DB Error"
        )
        mock_db_service_class.return_value = mock_db_service

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result is None

    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_no_processed_documents(
        self, mock_db_service_class
    ):
        """Test scenario with no successfully processed documents."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {
            "Items": [
                {
                    "document_id": "doc1",
                    "processing_status": DocumentProcessingStatus.processing.value,
                },
                {
                    "document_id": "doc2",
                    "processing_status": DocumentProcessingStatus.failed.value,
                },
            ]
        }

        # Act
        mock_db_service_class.return_value = mock_db_service
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )        # Assert
        assert result is None

    @patch("api_backend.utils.rag_query_processor.BEDROCK_RUNTIME_CLIENT")
    @patch("api_backend.utils.rag_query_processor.os")
    @patch("api_backend.utils.rag_query_processor.shutil")
    @patch("api_backend.utils.rag_query_processor.FAISS")
    @patch("api_backend.utils.rag_query_processor.S3Client")
    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_single_document_success(
        self,
        mock_db_service_class,
        mock_s3_client_class,
        mock_faiss,
        mock_shutil,
        mock_os,
        mock_bedrock_client,
    ):        # Local Modules
        from api_backend.utils.rag_query_processor import (
            FAISS_INDEX_CACHE,
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        document_id = "doc1"
        mock_logger = MagicMock()

        # Setup database service
        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {
            "Items": [
                {
                    "document_id": document_id,
                    "processing_status": DocumentProcessingStatus.completed.value,
                }
            ]
        }
        mock_db_service_class.return_value = mock_db_service

        # Setup S3 client
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        # Setup Bedrock client - use the mocked parameter
        mock_embedding_model = MagicMock()
        mock_bedrock_client.get_embedding_model.return_value = (
            mock_embedding_model
        )

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_faiss.load_local.return_value = mock_vector_store

        # Setup os.path and makedirs
        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs = MagicMock()

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result == mock_vector_store

        # Verify database call
        mock_db_service.list_document_records.assert_called_once_with(
            owner_id=owner_id, srd_id=srd_id
        )

        # Verify S3 downloads
        expected_faiss_key = (
            f"{owner_id}/{srd_id}/vector_store/{document_id}.faiss"
        )
        expected_pkl_key = (
            f"{owner_id}/{srd_id}/vector_store/{document_id}.pkl"
        )
        mock_s3_client.download_file.assert_any_call(
            object_key=expected_faiss_key,
            download_path=f"/tmp/test-owner_test-srd/{document_id}/{document_id}.faiss",
        )
        mock_s3_client.download_file.assert_any_call(
            object_key=expected_pkl_key,
            download_path=f"/tmp/test-owner_test-srd/{document_id}/{document_id}.pkl",
        )

        # Verify FAISS loading
        mock_faiss.load_local.assert_called_once()  # Verify cache update
        composite_key = f"{owner_id}#{srd_id}"
        assert FAISS_INDEX_CACHE[composite_key] == mock_vector_store

    @patch("api_backend.utils.rag_query_processor.os")
    @patch("api_backend.utils.rag_query_processor.shutil")
    @patch("api_backend.utils.rag_query_processor.FAISS")
    @patch("api_backend.utils.rag_query_processor.S3Client")
    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_multiple_documents_success(
        self,
        mock_db_service_class,
        mock_s3_client_class,
        mock_faiss,
        mock_shutil,
        mock_os,
        mock_bedrock_client,
    ):
        """Test successful loading and merging of multiple documents."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
            BEDROCK_RUNTIME_CLIENT,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup database service
        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {
            "Items": [
                {
                    "document_id": "doc1",
                    "processing_status": DocumentProcessingStatus.completed.value,
                },
                {
                    "document_id": "doc2",
                    "processing_status": DocumentProcessingStatus.completed.value,
                },
            ]
        }
        mock_db_service_class.return_value = mock_db_service

        # Setup S3 client
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        # Setup Bedrock client - mock the global instance directly
        mock_embedding_model = MagicMock()
        BEDROCK_RUNTIME_CLIENT.get_embedding_model.return_value = (
            mock_embedding_model
        )

        # Setup FAISS
        mock_vector_store1 = MagicMock()
        mock_vector_store2 = MagicMock()
        mock_faiss.load_local.side_effect = [
            mock_vector_store1,
            mock_vector_store2,
        ]

        # Setup os.path and makedirs
        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs = MagicMock()

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )        # Assert
        assert result == mock_vector_store1
        mock_vector_store1.merge_from.assert_called_once_with(
            mock_vector_store2  # First store is the base for merging
        )

    @patch("api_backend.utils.rag_query_processor.BEDROCK_RUNTIME_CLIENT")
    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    @patch("api_backend.utils.rag_query_processor.S3Client")
    @patch("api_backend.utils.rag_query_processor.shutil")
    @patch("api_backend.utils.rag_query_processor.os")
    def test_load_and_merge_faiss_indices_s3_error_continues(
        self,
        mock_os,
        mock_shutil,
        mock_s3_client_class,
        mock_db_service_class,
        mock_bedrock_client,
    ):        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup database service
        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {
            "Items": [
                {
                    "document_id": "doc1",
                    "processing_status": DocumentProcessingStatus.completed.value,
                }
            ]
        }
        mock_db_service_class.return_value = mock_db_service

        # Setup Bedrock client
        mock_embedding_model = MagicMock()
        mock_bedrock_client.get_embedding_model.return_value = (
            mock_embedding_model
        )

        # Setup S3 client to fail
        mock_s3_client = MagicMock()
        mock_s3_client.download_file.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey"}},
            operation_name="GetObject",
        )
        mock_s3_client_class.return_value = mock_s3_client

        # Setup os.path and makedirs
        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs = MagicMock()

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result is None  # No vector stores loaded successfully
        mock_logger.error.assert_called()

    @patch("api_backend.utils.rag_query_processor.os")
    @patch("api_backend.utils.rag_query_processor.shutil")
    @patch("api_backend.utils.rag_query_processor.FAISS")
    @patch("api_backend.utils.rag_query_processor.S3Client")
    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_missing_document_id(
        self,
        mock_db_service_class,
        mock_s3_client_class,
        mock_faiss,
        mock_shutil,
        mock_os,
    ):
        """Test scenario with documents missing document_id field."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
        )

        # Arrange
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {
            "Items": [
                {
                    # Missing document_id field
                    "processing_status": DocumentProcessingStatus.completed.value,
                },
                {
                    "document_id": "valid-doc",
                    "processing_status": DocumentProcessingStatus.completed.value,
                },
            ]
        }
        mock_db_service_class.return_value = mock_db_service

        # Set up S3 and FAISS mocks
        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        mock_vector_store = MagicMock()
        mock_faiss.load_local.return_value = mock_vector_store

        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs = MagicMock()

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result == mock_vector_store
        # Should only process one document (the valid one)
        assert mock_s3_client.download_file.call_count == 2  # .faiss and .pkl
        mock_faiss.load_local.assert_called_once()

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.time")
    def test_get_answer_from_rag_cache_hit(
        self, mock_time, mock_load_faiss, mock_dynamodb_class
    ):
        """Test cache hit scenario."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup time
        current_time = 1000
        mock_time.time.return_value = current_time

        # Setup DynamoDB
        mock_dynamodb = MagicMock()
        cached_response = {
            "answer": "cached answer",
            "ttl": str(current_time + 100),  # Valid cache
        }
        mock_dynamodb.get_item.return_value = cached_response
        mock_dynamodb_class.return_value = mock_dynamodb

        # Setup cache key
        cache_key_string = f"{owner_id}#{srd_id}-{query_text}-True"
        expected_hash = hashlib.md5(cache_key_string.encode()).hexdigest()

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert result == {"answer": "cached answer", "source": "cache"}
        mock_dynamodb.get_item.assert_called_once_with(
            key={"query_hash": expected_hash}
        )
        # Should not load FAISS indices since cache hit
        mock_load_faiss.assert_not_called()

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.time")
    def test_get_answer_from_rag_cache_expired(
        self, mock_time, mock_load_faiss, mock_dynamodb_class
    ):
        """Test cache expired scenario."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup time
        current_time = 1000
        mock_time.time.return_value = current_time

        # Setup DynamoDB with expired cache
        mock_dynamodb = MagicMock()
        cached_response = {
            "answer": "cached answer",
            "ttl": str(current_time - 100),  # Expired cache
        }
        mock_dynamodb.get_item.return_value = cached_response
        mock_dynamodb_class.return_value = mock_dynamodb

        # Setup FAISS loading to return None (will cause error)
        mock_load_faiss.return_value = None

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        # Should proceed to load FAISS since cache expired
        mock_load_faiss.assert_called_once()
        assert "error" in result  # Will fail due to no FAISS data

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    def test_get_answer_from_rag_no_llm_invoke_success(
        self, mock_load_faiss, mock_dynamodb_class
    ):
        """Test retrieval-only mode (no LLM invocation)."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Document 1 content"
        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Document 2 content"
        mock_retriever.invoke.return_value = [mock_doc1, mock_doc2]
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=False,  # No LLM invocation
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert result["source"] == "retrieval_only"
        assert "Document 1 content" in result["answer"]
        assert "Document 2 content" in result["answer"]
        mock_retriever.invoke.assert_called_once_with(query_text)

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    def test_get_answer_from_rag_no_llm_invoke_no_documents(
        self, mock_load_faiss, mock_dynamodb_class
    ):
        """Test retrieval-only mode with no documents found."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = []  # No documents
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=False,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert result["source"] == "retrieval_only"
        assert "No specific information found" in result["answer"]

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    def test_get_answer_from_rag_faiss_load_failure(
        self, mock_load_faiss, mock_dynamodb_class
    ):
        """Test FAISS loading failure."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS loading to fail
        mock_load_faiss.return_value = None

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=False,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert "error" in result
        assert "Could not load SRD data" in result["error"]

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.get_llm_instance")
    @patch("api_backend.utils.rag_query_processor.RetrievalQA")
    @patch("api_backend.utils.rag_query_processor.time")
    def test_get_answer_from_rag_llm_success(
        self,
        mock_time,
        mock_retrieval_qa,
        mock_get_llm,
        mock_load_faiss,
        mock_dynamodb_class,
    ):
        """Test successful LLM invocation."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup time
        current_time = 1000
        mock_time.time.return_value = current_time

        # Setup DynamoDB (no cache)
        mock_dynamodb = MagicMock()
        mock_dynamodb.get_item.return_value = None
        mock_dynamodb_class.return_value = mock_dynamodb

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Setup LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Setup RetrievalQA
        mock_qa_chain = MagicMock()
        mock_source_doc = MagicMock()
        mock_source_doc.page_content = "source content"
        mock_qa_result = {
            "result": "LLM generated answer",
            "source_documents": [mock_source_doc],
        }
        mock_qa_chain.invoke.return_value = mock_qa_result
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={"temperature": 0.5},
            lambda_logger=mock_logger,
        )

        # Assert
        assert result["answer"] == "LLM generated answer"
        assert result["source"] == "bedrock_llm"
        assert result["source_documents_retrieved"] == 1

        # Verify cache was updated
        mock_dynamodb.put_item.assert_called_once()
        cache_item = mock_dynamodb.put_item.call_args[1]["item"]
        assert cache_item["answer"] == "LLM generated answer"
        assert cache_item["owner_id"] == owner_id
        assert cache_item["srd_id"] == srd_id

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.get_llm_instance")
    def test_get_answer_from_rag_llm_init_failure(
        self, mock_get_llm, mock_load_faiss, mock_dynamodb_class
    ):
        """Test LLM initialization failure."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_load_faiss.return_value = mock_vector_store

        # Setup LLM to fail
        mock_get_llm.return_value = None

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert "error" in result
        assert (
            "Generative LLM component could not be configured"
            in result["error"]
        )

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.get_llm_instance")
    @patch("api_backend.utils.rag_query_processor.RetrievalQA")
    def test_get_answer_from_rag_conversational_style(
        self,
        mock_retrieval_qa,
        mock_get_llm,
        mock_load_faiss,
        mock_dynamodb_class,
    ):
        """Test conversational style formatting."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_qa_result = {
            "result": "LLM generated answer",
            "source_documents": [],
        }
        mock_qa_chain = MagicMock()
        mock_qa_chain.invoke.return_value = mock_qa_result
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=True,  # Enable conversational style
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        # Verify the query was formatted conversationally
        call_args = mock_qa_chain.invoke.call_args
        assert call_args[0][0]["query"] == f"User: {query_text}\nBot:"
        assert result["answer"] == "LLM generated answer"

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.get_llm_instance")
    @patch("api_backend.utils.rag_query_processor.RetrievalQA")
    def test_get_answer_from_rag_qa_chain_client_error(
        self,
        mock_retrieval_qa,
        mock_get_llm,
        mock_load_faiss,
        mock_dynamodb_class,
    ):
        """Test QA chain ClientError handling."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Setup LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Setup RetrievalQA to raise ClientError
        mock_qa_chain = MagicMock()
        mock_qa_chain.invoke.side_effect = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert "error" in result
        assert "Error communicating with the AI model" in result["error"]

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.get_llm_instance")
    @patch("api_backend.utils.rag_query_processor.RetrievalQA")
    def test_get_answer_from_rag_qa_chain_general_exception(
        self,
        mock_retrieval_qa,
        mock_get_llm,
        mock_load_faiss,
        mock_dynamodb_class,
    ):
        """Test QA chain general exception handling."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Setup LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        # Setup RetrievalQA to raise general exception
        mock_qa_chain = MagicMock()
        mock_qa_chain.invoke.side_effect = Exception("General error")
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        assert "error" in result
        assert (
            "Failed to generate an answer using the RAG chain"
            in result["error"]
        )

    def test_get_answer_from_rag_custom_number_of_documents(self):
        """Test custom number_of_documents parameter."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # This test focuses on the parameter being passed correctly
        with (
            patch("api_backend.utils.rag_query_processor.DynamoDb"),
            patch(
                "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
            ) as mock_load_faiss,
        ):

            # Setup FAISS
            mock_vector_store = MagicMock()
            mock_retriever = MagicMock()
            mock_retriever.invoke.return_value = []
            mock_vector_store.as_retriever.return_value = mock_retriever
            mock_load_faiss.return_value = mock_vector_store

            # Act
            result = get_answer_from_rag(
                query_text="test",
                owner_id="owner",
                srd_id="srd",
                invoke_generative_llm=False,
                use_conversational_style=False,
                generation_config_payload={},
                number_of_documents=10,
            )

            # Assert
            mock_vector_store.as_retriever.assert_called_once_with(
                search_kwargs={"k": 10}
            )
            assert result is not None  # Ensure function executed

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    def test_get_answer_from_rag_cache_error_continues(
        self, mock_dynamodb_class
    ):
        """Test that cache errors don't prevent processing."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        mock_dynamodb = MagicMock()
        mock_dynamodb.get_item.side_effect = ClientError(
            error_response={"Error": {"Code": "AccessDenied"}},
            operation_name="GetItem",
        )
        mock_dynamodb_class.return_value = mock_dynamodb

        with patch(
            "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
        ) as mock_load_faiss:
            mock_load_faiss.return_value = (
                None  # Will cause error but shows cache error was handled
            )

            # Act
            result = get_answer_from_rag(
                query_text="test",
                owner_id="owner",
                srd_id="srd",
                invoke_generative_llm=True,
                use_conversational_style=False,
                generation_config_payload={},
            )

            # Assert
            # Should continue processing despite cache error
            assert "error" in result
            assert "Could not load SRD data" in result["error"]

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    def test_get_answer_from_rag_retriever_creation_error(
        self, mock_load_faiss, mock_dynamo_class
    ):
        """Test when vector_store.as_retriever() fails with exception."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_answer_from_rag

        # Arrange
        mock_vector_store = MagicMock()
        mock_vector_store.as_retriever.side_effect = Exception("Retriever creation failed")
        mock_load_faiss.return_value = mock_vector_store

        # Act
        result = get_answer_from_rag(
            query_text="test query",
            owner_id="test-owner",
            srd_id="test-srd",
            invoke_generative_llm=False,
            use_conversational_style=False,
            generation_config_payload={},
            number_of_documents=4,
        )

        # Assert
        assert "error" in result
        assert "Failed to prepare for information retrieval" in result["error"]

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    @patch("api_backend.utils.rag_query_processor.get_llm_instance")
    @patch("api_backend.utils.rag_query_processor.RetrievalQA")
    @patch("api_backend.utils.rag_query_processor.time")
    def test_get_answer_from_rag_cache_put_error_continues(
        self,
        mock_time,
        mock_retrieval_qa,
        mock_get_llm,
        mock_load_faiss,
        mock_dynamodb_class,
    ):
        """Test that cache put errors don't prevent successful response."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            get_answer_from_rag,
        )

        # Arrange
        query_text = "test query"
        owner_id = "test-owner"
        srd_id = "test-srd"
        mock_logger = MagicMock()

        # Setup time
        current_time = 1000
        mock_time.time.return_value = current_time

        # Setup DynamoDB - get succeeds, put fails
        mock_dynamodb = MagicMock()
        mock_dynamodb.get_item.return_value = None
        mock_dynamodb.put_item.side_effect = ClientError(
            error_response={
                "Error": {"Code": "ProvisionedThroughputExceededException"}
            },
            operation_name="PutItem",
        )
        mock_dynamodb_class.return_value = mock_dynamodb

        # Setup FAISS
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Setup LLM
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm        # Setup RetrievalQA
        mock_qa_chain = MagicMock()
        mock_qa_result = {
            "result": "LLM generated answer",
            "source_documents": [MagicMock(page_content="test doc content")],  # Add a source document
        }
        mock_qa_chain.invoke.return_value = mock_qa_result
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain

        # Act
        result = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=True,
            use_conversational_style=False,
            generation_config_payload={},
            lambda_logger=mock_logger,
        )

        # Assert
        # Should still return successful result despite cache put error
        assert result["answer"] == "LLM generated answer"
        assert result["source"] == "bedrock_llm"
        assert result["source_documents_retrieved"] == 1

    @patch("api_backend.utils.rag_query_processor.os")
    @patch("api_backend.utils.rag_query_processor.shutil")
    @patch("api_backend.utils.rag_query_processor.FAISS")
    @patch("api_backend.utils.rag_query_processor.S3Client")
    @patch("api_backend.utils.rag_query_processor.DatabaseService")
    def test_load_and_merge_faiss_indices_cache_eviction(
        self,
        mock_db_service_class,
        mock_s3_client_class,
        mock_faiss,
        mock_shutil,
        mock_os,
    ):
        """Test cache eviction when MAX_CACHE_SIZE is reached."""
        # Local Modules
        from api_backend.utils.rag_query_processor import (
            _load_and_merge_faiss_indices_for_srd,
            FAISS_INDEX_CACHE,
            MAX_CACHE_SIZE,
        )

        # Arrange - Fill cache to maximum capacity
        FAISS_INDEX_CACHE.clear()
        for i in range(MAX_CACHE_SIZE):
            FAISS_INDEX_CACHE[f"owner{i}#srd{i}"] = MagicMock()

        owner_id = "new-owner"
        srd_id = "new-srd"
        mock_logger = MagicMock()

        # Set up mocks
        mock_db_service = MagicMock()
        mock_db_service.list_document_records.return_value = {
            "Items": [
                {
                    "document_id": "doc1",
                    "processing_status": DocumentProcessingStatus.completed.value,
                }
            ]
        }
        mock_db_service_class.return_value = mock_db_service

        mock_s3_client = MagicMock()
        mock_s3_client_class.return_value = mock_s3_client

        mock_vector_store = MagicMock()
        mock_faiss.load_local.return_value = mock_vector_store

        mock_os.path.join.side_effect = lambda *args: "/".join(args)
        mock_os.makedirs = MagicMock()

        # Capture the first key before eviction
        first_key = next(iter(FAISS_INDEX_CACHE))

        # Act
        result = _load_and_merge_faiss_indices_for_srd(
            owner_id, srd_id, mock_logger
        )

        # Assert
        assert result == mock_vector_store
        # Cache should still have MAX_CACHE_SIZE items
        assert len(FAISS_INDEX_CACHE) == MAX_CACHE_SIZE
        # New key should be in cache
        assert f"{owner_id}#{srd_id}" in FAISS_INDEX_CACHE
        # Oldest key should have been evicted
        assert first_key not in FAISS_INDEX_CACHE

    @patch("api_backend.utils.rag_query_processor.DynamoDb")
    @patch(
        "api_backend.utils.rag_query_processor._load_and_merge_faiss_indices_for_srd"
    )
    def test_get_answer_from_rag_retriever_invoke_error_no_llm(
        self, mock_load_faiss, mock_dynamo_class
    ):
        """Test retriever invoke error when not using LLM."""
        # Local Modules
        from api_backend.utils.rag_query_processor import get_answer_from_rag

        # Arrange
        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.invoke.side_effect = Exception("Retriever error")
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_load_faiss.return_value = mock_vector_store

        # Act
        result = get_answer_from_rag(
            query_text="test query",
            owner_id="test-owner",
            srd_id="test-srd",
            invoke_generative_llm=False,
            use_conversational_style=False,
            generation_config_payload={},
            number_of_documents=4,
        )

        # Assert
        assert "error" in result
        assert "Failed to prepare for information retrieval" in result["error"]
