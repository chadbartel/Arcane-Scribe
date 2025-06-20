"""Unit tests for the query router module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from fastapi import status

# Local Modules
from core.utils import ResponseSource
from api_backend.models import (
    User,
    RagQueryRequest,
    GenerationConfig,
)


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        username="test_user", email="test@example.com", groups=["users"]
    )


@pytest.fixture
def mock_get_answer_from_rag():
    """Create a mock for the get_answer_from_rag function."""
    with patch("api_backend.routers.query.get_answer_from_rag") as mock:
        mock.return_value = {
            "answer": "Test answer from RAG",
            "source_documents_retrieved": 3,
            "source": ResponseSource.bedrock_llm.value,
        }
        yield mock


@pytest.fixture
def query_router_with_mocks(mock_get_answer_from_rag):
    """Create query router with mocked dependencies."""
    # Local Modules
    from api_backend.routers import query

    yield query


class TestQueryEndpoint:
    """Test cases for the query_endpoint function."""

    def test_query_endpoint_success_basic(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test successful query with basic parameters."""
        # Arrange
        request = RagQueryRequest(
            query_text="What is the meaning of life?", srd_id="test_srd_123"
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify get_answer_from_rag was called with correct parameters
        mock_get_answer_from_rag.assert_called_once_with(
            query_text="What is the meaning of life?",
            owner_id="test_user",
            srd_id="test_srd_123",
            invoke_generative_llm=False,
            use_conversational_style=False,
            generation_config_payload={},
            number_of_documents=4,  # default value
            lambda_logger=query_router_with_mocks.logger,
        )

        # Check response content
        response_content = eval(response.body.decode())
        assert response_content["answer"] == "Test answer from RAG"
        assert response_content["source_documents_retrieved"] == 3

    def test_query_endpoint_with_all_parameters(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query with all optional parameters set."""
        # Arrange
        generation_config = GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            max_token_count=1000,
            stop_sequences=["END", "STOP"],
        )

        request = RagQueryRequest(
            query_text="  How does magic work?  ",  # With whitespace
            srd_id="  test_srd_456  ",  # With whitespace
            invoke_generative_llm=True,
            use_conversation_style=True,
            generation_config=generation_config,
            number_of_documents=8,
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify get_answer_from_rag was called with correct parameters
        mock_get_answer_from_rag.assert_called_once_with(
            query_text="How does magic work?",  # Stripped
            owner_id="test_user",
            srd_id="test_srd_456",  # Stripped
            invoke_generative_llm=True,
            use_conversational_style=True,
            generation_config_payload={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_token_count": 1000,
                "stop_sequences": ["END", "STOP"],
            },
            number_of_documents=8,
            lambda_logger=query_router_with_mocks.logger,
        )

    def test_query_endpoint_with_none_generation_config(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query with None generation config."""
        # Arrange
        request = RagQueryRequest(
            query_text="Test query", srd_id="test_srd", generation_config=None
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify generation_config_payload is empty dict
        call_args = mock_get_answer_from_rag.call_args
        assert call_args[1]["generation_config_payload"] == {}

    def test_query_endpoint_request_parsing_error(
        self, query_router_with_mocks, mock_user
    ):
        """Test query endpoint with request parsing error."""
        # Arrange - Create a request that will cause an error during processing
        request = MagicMock()
        request.query_text.strip.side_effect = AttributeError(
            "No strip method"
        )
        request.model_dump_json.return_value = '{"test": "data"}'

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_content = eval(response.body.decode())
        assert "error" in response_content
        assert "Malformed request:" in response_content["error"]

    def test_query_endpoint_rag_returns_error_not_found(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query when RAG processor returns 'Could not load SRD data' error."""
        # Arrange
        mock_get_answer_from_rag.return_value = {
            "error": "Could not load SRD data for the given parameters"
        }

        request = RagQueryRequest(
            query_text="Test query", srd_id="nonexistent_srd"
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_content = eval(response.body.decode())
        assert "Could not load SRD data" in response_content["error"]

    def test_query_endpoint_rag_returns_error_service_unavailable(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query when RAG processor returns 'components not ready' error."""
        # Arrange
        mock_get_answer_from_rag.return_value = {
            "error": "System components not ready for processing"
        }

        request = RagQueryRequest(query_text="Test query", srd_id="test_srd")

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        response_content = eval(response.body.decode())
        assert "components not ready" in response_content["error"]

    def test_query_endpoint_rag_returns_error_internal_server_error(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query when RAG processor returns other types of errors."""
        # Arrange
        mock_get_answer_from_rag.return_value = {
            "error": "Database connection failed"
        }

        request = RagQueryRequest(query_text="Test query", srd_id="test_srd")

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_content = eval(response.body.decode())
        assert "Database connection failed" in response_content["error"]

    def test_query_endpoint_rag_raises_exception(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query when RAG processor raises an exception."""
        # Arrange
        mock_get_answer_from_rag.side_effect = Exception(
            "Unexpected error occurred"
        )

        request = RagQueryRequest(query_text="Test query", srd_id="test_srd")

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_content = eval(response.body.decode())
        assert "error" in response_content
        assert "Internal server error:" in response_content["error"]
        assert "Unexpected error occurred" in response_content["error"]

    def test_query_endpoint_composite_key_generation(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test that composite key is generated correctly."""
        # Arrange
        request = RagQueryRequest(query_text="Test query", srd_id="test_srd")

        # Act
        query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert - Check that the logging contains the expected composite key
        # The composite key should be "test_user#test_srd"
        mock_get_answer_from_rag.assert_called_once()
        call_args = mock_get_answer_from_rag.call_args
        assert call_args[1]["owner_id"] == "test_user"
        assert call_args[1]["srd_id"] == "test_srd"

    def test_query_endpoint_default_boolean_values(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test that boolean flags default to False when not provided."""
        # Arrange
        request = RagQueryRequest(
            query_text="Test query",
            srd_id="test_srd",
            # Not setting invoke_generative_llm or use_conversation_style
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        call_args = mock_get_answer_from_rag.call_args
        assert call_args[1]["invoke_generative_llm"] is False
        assert call_args[1]["use_conversational_style"] is False

    def test_query_endpoint_boolean_values_explicit_false(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test that boolean flags work when explicitly set to False."""
        # Arrange
        request = RagQueryRequest(
            query_text="Test query",
            srd_id="test_srd",
            invoke_generative_llm=False,
            use_conversation_style=False,
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        call_args = mock_get_answer_from_rag.call_args
        assert call_args[1]["invoke_generative_llm"] is False
        assert call_args[1]["use_conversational_style"] is False

    def test_query_endpoint_number_of_documents_default(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test that number_of_documents defaults to 4."""
        # Arrange
        request = RagQueryRequest(
            query_text="Test query",
            srd_id="test_srd",
            # Not setting number_of_documents
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        call_args = mock_get_answer_from_rag.call_args
        assert call_args[1]["number_of_documents"] == 4

    def test_query_endpoint_empty_strings_stripped(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test that empty strings after stripping are handled."""
        # Arrange
        request = RagQueryRequest(
            query_text="   ",  # Only whitespace
            srd_id="   ",  # Only whitespace
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        call_args = mock_get_answer_from_rag.call_args
        assert call_args[1]["query_text"] == ""
        assert call_args[1]["srd_id"] == ""

    def test_query_endpoint_generation_config_partial(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test query with partial generation config."""
        # Arrange
        generation_config = GenerationConfig(
            temperature=0.5,
            # Only setting temperature, leaving others as None
        )

        request = RagQueryRequest(
            query_text="Test query",
            srd_id="test_srd",
            generation_config=generation_config,
        )

        # Act
        response = query_router_with_mocks.query_endpoint(
            current_user=mock_user, request=request
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        call_args = mock_get_answer_from_rag.call_args
        config_payload = call_args[1]["generation_config_payload"]
        assert config_payload["temperature"] == 0.5
        assert (
            "top_p" in config_payload
        )  # Should be None in the serialized form
        assert "max_token_count" in config_payload  # Should be None
        assert "stop_sequences" in config_payload  # Should be None


class TestRouterIntegration:
    """Integration tests for the query router."""

    def test_router_endpoint_exists(self, query_router_with_mocks):
        """Test that the expected endpoint exists in the router."""
        # Get the router instance
        router = query_router_with_mocks.router

        # Check that router has the expected route
        route_paths = [route.path for route in router.routes]
        assert "/query" in route_paths

    def test_router_methods(self, query_router_with_mocks):
        """Test that route has correct HTTP method."""
        router = query_router_with_mocks.router

        # Find the route and check method
        for route in router.routes:
            if route.path == "/query":
                assert "POST" in route.methods
                break
        else:
            pytest.fail("Route /query not found")

    def test_router_prefix(self, query_router_with_mocks):
        """Test that router has correct prefix."""
        router = query_router_with_mocks.router
        assert router.prefix == "/query"

    def test_router_tags(self, query_router_with_mocks):
        """Test that router has correct tags."""
        router = query_router_with_mocks.router
        assert "Query" in router.tags

    def test_different_users_different_composite_keys(
        self, query_router_with_mocks, mock_get_answer_from_rag
    ):
        """Test that different users generate different composite keys."""
        # Arrange
        user1 = User(
            username="user1", email="user1@test.com", groups=["users"]
        )
        user2 = User(
            username="user2", email="user2@test.com", groups=["users"]
        )

        request = RagQueryRequest(query_text="Test query", srd_id="same_srd")

        # Act - First user
        query_router_with_mocks.query_endpoint(
            current_user=user1, request=request
        )

        first_call_args = mock_get_answer_from_rag.call_args

        # Reset mock
        mock_get_answer_from_rag.reset_mock()

        # Act - Second user
        query_router_with_mocks.query_endpoint(
            current_user=user2, request=request
        )

        second_call_args = mock_get_answer_from_rag.call_args

        # Assert
        assert first_call_args[1]["owner_id"] == "user1"
        assert second_call_args[1]["owner_id"] == "user2"
        assert first_call_args[1]["srd_id"] == "same_srd"
        assert second_call_args[1]["srd_id"] == "same_srd"

    def test_error_logging_contains_composite_key(
        self, query_router_with_mocks, mock_user, mock_get_answer_from_rag
    ):
        """Test that error logging includes the composite key."""
        # Arrange
        mock_get_answer_from_rag.side_effect = Exception("Test exception")

        request = RagQueryRequest(
            query_text="Test query", srd_id="test_srd"
        )  # Act
        with patch.object(
            query_router_with_mocks.logger, "exception"
        ) as mock_log:
            response = query_router_with_mocks.query_endpoint(
                current_user=mock_user, request=request
            )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Check that logging was called with composite key
        mock_log.assert_called_once()
        log_message = mock_log.call_args[0][0]
        assert "test_user#test_srd" in log_message
