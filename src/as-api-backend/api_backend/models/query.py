"""Pydantic models for RAG query validation."""

# Standard Library
from typing import List, Optional

# Third Party
from pydantic import BaseModel, Field, ConfigDict

# Local Modules
from core.utils import ResponseSource


class GenerationConfig(BaseModel):
    """Configuration settings for text generation.

    Attributes:
        temperature: Controls randomness in generation (0.0-1.0).
        top_p: Controls nucleus sampling for token selection.
        max_token_count: Maximum number of tokens to generate.
        stop_sequences: List of sequences that stop generation.
    """

    model_config = ConfigDict(populate_by_name=True)

    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Temperature for controlling randomness in generation",
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-p value for nucleus sampling",
    )
    max_token_count: Optional[int] = Field(
        default=None,
        gt=0,
        le=200000,
        description="Maximum number of tokens to generate",
        alias="max_tokens",
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None,
        description="List of sequences that will stop generation",
    )


class RagQueryRequest(BaseModel):
    """Request model for RAG (Retrieval-Augmented Generation) queries.

    Attributes:
        query_text: The text query to process.
        invoke_generative_llm: Whether to use generative LLM for response.
        use_conversation_style: Whether to format response conversationally.
        generation_config: Configuration for text generation parameters.
        srd_id: System Reference Document identifier.
        number_of_documents: Number of documents to retrieve from the source.
    """

    model_config = ConfigDict(populate_by_name=True)

    query_text: str = Field(..., description="The query text to process")
    invoke_generative_llm: Optional[bool] = Field(
        default=False,
        description="Whether to invoke generative LLM for response",
    )
    use_conversation_style: Optional[bool] = Field(
        default=False,
        description="Whether to use conversational response style",
    )
    generation_config: Optional[GenerationConfig] = Field(
        default=None, description="Configuration settings for text generation"
    )
    srd_id: str = Field(
        ..., description="System Reference Document identifier"
    )
    number_of_documents: Optional[int] = Field(
        default=4,
        ge=1,
        description="Number of documents to retrieve from the source",
    )


class SourceDocument(BaseModel):
    """Model representing a source document.

    Attributes:
        source: The filename of the document.
        page: The page number of the document.
        content: The content of the source document.
    """

    model_config = ConfigDict(populate_by_name=True)

    source: Optional[str] = Field(
        None, description="Source filename of the document"
    )
    page: Optional[int] = Field(
        None, ge=1, description="Page number of the document"
    )
    content: Optional[str] = Field(
        None, description="Content of the source document"
    )


class RagQueryResponse(BaseModel):
    """Response model for RAG (Retrieval-Augmented Generation) queries.

    Attributes:
        answer: The generated answer text from the RAG system.
        source_documents_retrieved: Number of documents retrieved from the source.
        source: The source type indicating how the response was generated.
    """

    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(
        ..., description="The generated answer text from the RAG system"
    )
    source_documents_retrieved: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of documents retrieved from the source",
    )
    source_documents_content: Optional[List[SourceDocument]] = Field(
        default=None,
        description="List of source documents retrieved for the query",
    )
    source: ResponseSource = Field(
        ...,
        description="The source type indicating how response was generated",
    )


class RagQueryErrorResponse(BaseModel):
    """Error response model for RAG query failures.

    Attributes:
        error: The error message describing the issue.
    """

    model_config = ConfigDict(populate_by_name=True)

    error: str = Field(..., description="Error message describing the issue.")
