# Standard Library
from enum import Enum


class AllowedMethod(str, Enum):
    """Enumeration of allowed HTTP methods.

    Attributes:
        get: HTTP GET method.
        post: HTTP POST method.
        put: HTTP PUT method.
        delete: HTTP DELETE method.
        patch: HTTP PATCH method.
        head: HTTP HEAD method.
    """

    get = "GET"
    post = "POST"
    put = "PUT"
    delete = "DELETE"
    patch = "PATCH"
    head = "HEAD"


class ResponseSource(str, Enum):
    """Enumeration of possible response sources.

    Attributes:
        retrieval_only: Response generated using only retrieval methods.
        bedrock_llm: Response generated using Bedrock LLM.
    """

    retrieval_only = "retrieval_only"
    bedrock_llm = "bedrock_llm"


class DocumentProcessingStatus(str, Enum):
    """Enumeration of document processing statuses.

    Attributes:
        pending: Document is pending processing.
        processing: Document is currently being processed.
        completed: Document processing is completed.
        failed: Document processing has failed.
    """

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class CognitoGroup(str, Enum):
    """Enumeration of Cognito user groups.

    Attributes:
        admin: Admin group with elevated privileges.
        user: Regular user group with standard permissions.
    """

    admins = "admins"
    users = "users"
