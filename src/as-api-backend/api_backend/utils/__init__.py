"""Utility functions for the API backend.

This module provides helper functions that can be used across the API backend.
"""

# Local Modules
from api_backend.utils.rag_query_processor import get_answer_from_rag

__all__ = [
    "get_answer_from_rag",
]
