"""Utility functions for the API backend.

This module provides helper functions that can be used across the API backend.
"""

# Local Modules
from api_backend.utils.enums import (
    AllowedMethod,
    ResponseSource,
    DocumentProcessingStatus
)
from api_backend.utils.rag_query_processor import get_answer_from_rag
from api_backend.utils.presigned_url_generator import generate_presigned_url
from api_backend.utils.helpers import extract_username_from_basic_auth

__all__ = [
    "AllowedMethod",
    "ResponseSource",
    "DocumentProcessingStatus",
    "get_answer_from_rag",
    "generate_presigned_url",
    "extract_username_from_basic_auth",
]
