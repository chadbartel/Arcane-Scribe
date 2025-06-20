"""Unit tests for the bedrock_runtime module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# Local Modules
from pdf_ingestor.aws.bedrock_runtime import BedrockRuntimeClient


class TestBedrockRuntimeClient:
    """Test cases for the BedrockRuntimeClient class."""

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_init_success_with_region(self, mock_boto3_client):
        """Test successful initialization with region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        region_name = "us-east-1"

        client = BedrockRuntimeClient(region_name=region_name)

        mock_boto3_client.assert_called_once_with(
            "bedrock-runtime", region_name=region_name
        )
        assert client.client == mock_client

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_init_success_without_region(self, mock_boto3_client):
        """Test successful initialization without region_name."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        client = BedrockRuntimeClient()

        mock_boto3_client.assert_called_once_with(
            "bedrock-runtime", region_name=None
        )
        assert client.client == mock_client

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    @patch("pdf_ingestor.aws.bedrock_runtime.logger")
    def test_init_failure_no_credentials(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to missing credentials."""
        error = NoCredentialsError()
        mock_boto3_client.side_effect = error

        with pytest.raises(NoCredentialsError):
            BedrockRuntimeClient()

        mock_logger.error.assert_called_once_with(
            f"Failed to create Bedrock Runtime client: {error}"
        )

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    @patch("pdf_ingestor.aws.bedrock_runtime.logger")
    def test_init_failure_client_error(self, mock_logger, mock_boto3_client):
        """Test initialization failure due to AWS client error."""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "CreateClient",
        )
        mock_boto3_client.side_effect = error

        with pytest.raises(ClientError):
            BedrockRuntimeClient()

        mock_logger.error.assert_called_once_with(
            f"Failed to create Bedrock Runtime client: {error}"
        )

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    @patch("pdf_ingestor.aws.bedrock_runtime.logger")
    def test_init_failure_generic_exception(
        self, mock_logger, mock_boto3_client
    ):
        """Test initialization failure due to generic exception."""
        error = ValueError("Invalid configuration")
        mock_boto3_client.side_effect = error

        with pytest.raises(ValueError):
            BedrockRuntimeClient()

        mock_logger.error.assert_called_once_with(
            f"Failed to create Bedrock Runtime client: {error}"
        )

    @patch("pdf_ingestor.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_get_embedding_model_success(
        self, mock_boto3_client, mock_bedrock_embeddings
    ):
        """Test successful creation of embedding model."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_embedding_instance = MagicMock()
        mock_bedrock_embeddings.return_value = mock_embedding_instance
        model_id = "amazon.titan-embed-text-v1"

        client = BedrockRuntimeClient()
        result = client.get_embedding_model(model_id)

        mock_bedrock_embeddings.assert_called_once_with(
            client=mock_client, model_id=model_id
        )
        assert result == mock_embedding_instance

    @patch("pdf_ingestor.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_get_embedding_model_with_different_model_id(
        self, mock_boto3_client, mock_bedrock_embeddings
    ):
        """Test embedding model creation with different model ID."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_embedding_instance = MagicMock()
        mock_bedrock_embeddings.return_value = mock_embedding_instance
        model_id = "cohere.embed-english-v3"

        client = BedrockRuntimeClient()
        result = client.get_embedding_model(model_id)

        mock_bedrock_embeddings.assert_called_once_with(
            client=mock_client, model_id=model_id
        )
        assert result == mock_embedding_instance

    @patch("pdf_ingestor.aws.bedrock_runtime.ChatBedrock")
    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_success_without_kwargs(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test successful creation of chat model without model_kwargs."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "amazon.titan-text-express-v1"

        client = BedrockRuntimeClient()
        result = client.get_chat_model(model_id)

        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=None,
        )
        assert result == mock_chat_instance

    @patch("pdf_ingestor.aws.bedrock_runtime.ChatBedrock")
    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_success_with_kwargs(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test successful creation of chat model with model_kwargs."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        model_kwargs = {
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.9,
        }

        client = BedrockRuntimeClient()
        result = client.get_chat_model(model_id, model_kwargs)

        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=model_kwargs,
        )
        assert result == mock_chat_instance

    @patch("pdf_ingestor.aws.bedrock_runtime.ChatBedrock")
    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_success_with_empty_kwargs(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test successful creation of chat model with empty model_kwargs."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "amazon.titan-text-premier-v1:0"
        model_kwargs = {}

        client = BedrockRuntimeClient()
        result = client.get_chat_model(model_id, model_kwargs)

        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=model_kwargs,
        )
        assert result == mock_chat_instance

    @patch("pdf_ingestor.aws.bedrock_runtime.ChatBedrock")
    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_with_different_model_id(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test chat model creation with different model ID."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "meta.llama3-70b-instruct-v1:0"

        client = BedrockRuntimeClient()
        result = client.get_chat_model(model_id)

        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=None,
        )
        assert result == mock_chat_instance

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_client_attribute_persistence(self, mock_boto3_client):
        """Test that the client attribute persists across method calls."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        client = BedrockRuntimeClient()

        # Verify client is stored correctly
        assert client.client == mock_client

        # Make multiple method calls and verify same client is used
        with (
            patch(
                "pdf_ingestor.aws.bedrock_runtime.BedrockEmbeddings"
            ) as mock_embeddings,
            patch("pdf_ingestor.aws.bedrock_runtime.ChatBedrock") as mock_chat,
        ):

            client.get_embedding_model("test-embedding-model")
            client.get_chat_model("test-chat-model")

            # Verify both calls used the same client instance
            mock_embeddings.assert_called_once_with(
                client=mock_client, model_id="test-embedding-model"
            )
            mock_chat.assert_called_once_with(
                client=mock_client,
                model="test-chat-model",
                model_kwargs=None,
            )

    @patch("pdf_ingestor.aws.bedrock_runtime.boto3.client")
    def test_multiple_instances_independent(self, mock_boto3_client):
        """Test that multiple client instances are independent."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_boto3_client.side_effect = [mock_client1, mock_client2]

        client1 = BedrockRuntimeClient(region_name="us-east-1")
        client2 = BedrockRuntimeClient(region_name="us-west-2")

        assert client1.client == mock_client1
        assert client2.client == mock_client2
        assert client1.client != client2.client

        # Verify both clients were created with correct regions
        assert mock_boto3_client.call_count == 2
        mock_boto3_client.assert_any_call(
            "bedrock-runtime", region_name="us-east-1"
        )
        mock_boto3_client.assert_any_call(
            "bedrock-runtime", region_name="us-west-2"
        )
