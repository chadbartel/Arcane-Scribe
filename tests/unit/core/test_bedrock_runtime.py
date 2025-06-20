"""Unit tests for the bedrock_runtime module."""

# Standard Library
from unittest.mock import MagicMock, patch

# Third Party
import pytest
from botocore.exceptions import ClientError, NoCredentialsError

# Local Modules
from core.aws.bedrock_runtime import BedrockRuntimeClient


class TestBedrockRuntimeClient:
    """Test cases for the BedrockRuntimeClient class."""

    def setup_method(self):
        """Reset global variables before each test."""
        # Import the module to reset global variables
        import core.aws.bedrock_runtime

        core.aws.bedrock_runtime._bedrock_runtime_client = None
        core.aws.bedrock_runtime._embedding_model_instance = None

    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_boto_client_first_call(self, mock_boto3_client):
        """Test that _get_boto_client initializes client on first call."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        client = BedrockRuntimeClient()
        result = client._get_boto_client()

        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        assert result == mock_client

    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_boto_client_subsequent_calls(self, mock_boto3_client):
        """Test that _get_boto_client reuses existing client."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        client = BedrockRuntimeClient()

        # First call
        result1 = client._get_boto_client()
        # Second call
        result2 = client._get_boto_client()

        # boto3.client should only be called once
        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        assert result1 == mock_client
        assert result2 == mock_client
        assert result1 is result2

    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_boto_client_exception_propagated(self, mock_boto3_client):
        """Test that exceptions during client creation are propagated."""
        error = NoCredentialsError()
        mock_boto3_client.side_effect = error

        client = BedrockRuntimeClient()

        with pytest.raises(NoCredentialsError):
            client._get_boto_client()

    @patch("core.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_embedding_model_first_call(
        self, mock_boto3_client, mock_bedrock_embeddings
    ):
        """Test embedding model creation on first call."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_embedding_instance = MagicMock()
        mock_bedrock_embeddings.return_value = mock_embedding_instance
        model_id = "amazon.titan-embed-text-v1"

        client = BedrockRuntimeClient()
        result = client.get_embedding_model(model_id)

        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        mock_bedrock_embeddings.assert_called_once_with(
            client=mock_client, model_id=model_id
        )
        assert result == mock_embedding_instance

    @patch("core.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_embedding_model_subsequent_calls_same_instance(
        self, mock_boto3_client, mock_bedrock_embeddings
    ):
        """Test that subsequent calls return the same embedding instance."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_embedding_instance = MagicMock()
        mock_bedrock_embeddings.return_value = mock_embedding_instance

        client = BedrockRuntimeClient()

        # First call
        result1 = client.get_embedding_model("model1")
        # Second call with different model_id (should still return same instance)
        result2 = client.get_embedding_model("model2")

        # BedrockEmbeddings should only be created once
        mock_bedrock_embeddings.assert_called_once_with(
            client=mock_client, model_id="model1"
        )
        assert result1 == mock_embedding_instance
        assert result2 == mock_embedding_instance
        assert result1 is result2

    @patch("core.aws.bedrock_runtime.ChatBedrock")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_without_kwargs(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test chat model creation without model_kwargs."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "amazon.titan-text-express-v1"

        client = BedrockRuntimeClient()
        result = client.get_chat_model(model_id)

        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=None,
        )
        assert result == mock_chat_instance

    @patch("core.aws.bedrock_runtime.ChatBedrock")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_with_kwargs(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test chat model creation with model_kwargs."""
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

        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=model_kwargs,
        )
        assert result == mock_chat_instance

    @patch("core.aws.bedrock_runtime.ChatBedrock")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_with_empty_kwargs(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test chat model creation with empty model_kwargs."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "amazon.titan-text-premier-v1:0"
        model_kwargs = {}

        client = BedrockRuntimeClient()
        result = client.get_chat_model(model_id, model_kwargs)

        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        mock_chat_bedrock.assert_called_once_with(
            client=mock_client,
            model=model_id,
            model_kwargs=model_kwargs,
        )
        assert result == mock_chat_instance

    @patch("core.aws.bedrock_runtime.ChatBedrock")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_get_chat_model_multiple_calls_create_new_instances(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test that each call to get_chat_model creates a new ChatBedrock instance."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance1 = MagicMock()
        mock_chat_instance2 = MagicMock()
        mock_chat_bedrock.side_effect = [
            mock_chat_instance1,
            mock_chat_instance2,
        ]

        client = BedrockRuntimeClient()

        # First call
        result1 = client.get_chat_model("model1")
        # Second call
        result2 = client.get_chat_model("model2")

        # boto3.client should only be called once (cached)
        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        # ChatBedrock should be called twice (new instance each time)
        assert mock_chat_bedrock.call_count == 2
        assert result1 == mock_chat_instance1
        assert result2 == mock_chat_instance2
        assert result1 is not result2

    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_multiple_client_instances_share_global_state(
        self, mock_boto3_client
    ):
        """Test that multiple BedrockRuntimeClient instances share global state."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        client1 = BedrockRuntimeClient()
        client2 = BedrockRuntimeClient()

        # Both clients should use the same underlying boto3 client
        result1 = client1._get_boto_client()
        result2 = client2._get_boto_client()

        # boto3.client should only be called once due to global caching
        mock_boto3_client.assert_called_once_with("bedrock-runtime")
        assert result1 == mock_client
        assert result2 == mock_client
        assert result1 is result2

    @patch("core.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_embedding_model_shared_across_instances(
        self, mock_boto3_client, mock_bedrock_embeddings
    ):
        """Test that embedding model is shared across BedrockRuntimeClient instances."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_embedding_instance = MagicMock()
        mock_bedrock_embeddings.return_value = mock_embedding_instance

        client1 = BedrockRuntimeClient()
        client2 = BedrockRuntimeClient()

        # Both clients should get the same embedding instance
        result1 = client1.get_embedding_model("model1")
        result2 = client2.get_embedding_model("model2")

        # BedrockEmbeddings should only be created once
        mock_bedrock_embeddings.assert_called_once_with(
            client=mock_client, model_id="model1"
        )
        assert result1 == mock_embedding_instance
        assert result2 == mock_embedding_instance
        assert result1 is result2

    @patch("core.aws.bedrock_runtime.logger")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_logging_in_get_boto_client(self, mock_boto3_client, mock_logger):
        """Test that _get_boto_client logs appropriate messages."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        client = BedrockRuntimeClient()
        client._get_boto_client()

        mock_logger.info.assert_called_with(
            "Checking if Bedrock runtime client is initialized."
        )

    @patch("core.aws.bedrock_runtime.logger")
    @patch("core.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_logging_in_get_embedding_model(
        self, mock_boto3_client, mock_bedrock_embeddings, mock_logger
    ):
        """Test that get_embedding_model logs appropriate messages."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_embedding_instance = MagicMock()
        mock_bedrock_embeddings.return_value = mock_embedding_instance

        client = BedrockRuntimeClient()
        client.get_embedding_model("test-model")

        # Should log both boto client and embedding model checks
        mock_logger.info.assert_any_call(
            "Checking if Bedrock runtime client is initialized."
        )
        mock_logger.info.assert_any_call(
            "Checking if embedding model instance is initialized."
        )

    @patch("core.aws.bedrock_runtime.logger")
    @patch("core.aws.bedrock_runtime.ChatBedrock")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_logging_in_get_chat_model(
        self, mock_boto3_client, mock_chat_bedrock, mock_logger
    ):
        """Test that get_chat_model logs appropriate messages."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_chat_instance = MagicMock()
        mock_chat_bedrock.return_value = mock_chat_instance
        model_id = "test-model"

        client = BedrockRuntimeClient()
        client.get_chat_model(model_id)

        # Should log both boto client check and chat model creation
        mock_logger.info.assert_any_call(
            "Checking if Bedrock runtime client is initialized."
        )
        mock_logger.info.assert_any_call(
            "Creating ChatBedrock instance with model ID: %s", model_id
        )

    @patch("core.aws.bedrock_runtime.BedrockEmbeddings")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_embedding_model_exception_propagated(
        self, mock_boto3_client, mock_bedrock_embeddings
    ):
        """Test that exceptions during embedding model creation are propagated."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ValueError("Invalid model configuration")
        mock_bedrock_embeddings.side_effect = error

        client = BedrockRuntimeClient()

        with pytest.raises(ValueError, match="Invalid model configuration"):
            client.get_embedding_model("invalid-model")

    @patch("core.aws.bedrock_runtime.ChatBedrock")
    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_chat_model_exception_propagated(
        self, mock_boto3_client, mock_chat_bedrock
    ):
        """Test that exceptions during chat model creation are propagated."""
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "CreateChatModel",
        )
        mock_chat_bedrock.side_effect = error

        client = BedrockRuntimeClient()

        with pytest.raises(ClientError):
            client.get_chat_model("test-model")

    @patch("core.aws.bedrock_runtime.boto3.client")
    def test_client_creation_with_botocore_client_error(
        self, mock_boto3_client
    ):
        """Test that boto3 client creation errors are propagated."""
        error = ClientError(
            {
                "Error": {
                    "Code": "ServiceUnavailable",
                    "Message": "Service unavailable",
                }
            },
            "CreateClient",
        )
        mock_boto3_client.side_effect = error

        client = BedrockRuntimeClient()

        with pytest.raises(ClientError):
            client._get_boto_client()

    def test_class_instantiation_no_args(self):
        """Test that BedrockRuntimeClient can be instantiated without arguments."""
        client = BedrockRuntimeClient()
        assert isinstance(client, BedrockRuntimeClient)
