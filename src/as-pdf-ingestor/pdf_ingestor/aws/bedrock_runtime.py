"""Bedrock runtime client wrapper for AWS Bedrock services."""

# Standard Library
from typing import Dict, Any, Optional

# Third Party
import boto3
from aws_lambda_powertools import Logger
from langchain_aws import (
    BedrockEmbeddings,
    ChatBedrock,
)

# Initialize logger
logger = Logger(service="bedrock-runtime-client-wrapper")

# Define global variables for your clients, but initialize them to None
_bedrock_runtime_client: Optional[boto3.client] = None
_embedding_model_instance: Optional[BedrockEmbeddings] = None


class BedrockRuntimeClient:
    """
    A client wrapper for AWS Bedrock Runtime services.
    """

    def _get_boto_client(self) -> boto3.client:
        """Lazily initializes and returns a boto3 bedrock-runtime client.

        Returns
        -------
        boto3.client
            An initialized boto3 client for AWS Bedrock Runtime.
        """
        global _bedrock_runtime_client

        # Check if the client is already initialized
        logger.info("Checking if Bedrock runtime client is initialized.")
        if _bedrock_runtime_client is None:
            _bedrock_runtime_client = boto3.client("bedrock-runtime")
        return _bedrock_runtime_client

    def get_embedding_model(
        self,
        model_id: str,
    ) -> BedrockEmbeddings:
        """Get an embedding model from AWS Bedrock.

        This method initializes a BedrockEmbeddings instance if it hasn't been
        created yet, and returns it. The instance is created with the provided
        model_id and the lazily initialized Bedrock runtime client.

        Parameters
        ----------
        model_id : str
            _description_

        Returns
        -------
        BedrockEmbeddings
            _description_
        """
        global _embedding_model_instance

        # Ensure the Bedrock runtime client is initialized
        logger.info("Checking if embedding model instance is initialized.")
        if _embedding_model_instance is None:
            _embedding_model_instance = BedrockEmbeddings(
                client=self._get_boto_client(), model_id=model_id
            )
        return _embedding_model_instance

    def get_chat_model(
        self,
        model_id: str,
        model_kwargs: Optional[Dict[str, Any]] = None,
    ) -> ChatBedrock:
        """
        Get a chat model from AWS Bedrock.

        Parameters
        ----------
        model_id : str
            The ID of the Bedrock model to use for chat.
        max_retries : int
            The maximum number of retries for the chat model.
        retry_delay : float
            The delay between retries in seconds.

        Returns
        -------
        ChatBedrock
            An instance of ChatBedrock configured with the specified model.
        """
        logger.info(
            "Creating ChatBedrock instance with model ID: %s", model_id
        )
        return ChatBedrock(
            client=self._get_boto_client(),
            model=model_id,
            model_kwargs=model_kwargs,
        )
