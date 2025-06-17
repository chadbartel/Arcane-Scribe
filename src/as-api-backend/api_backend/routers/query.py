# Standard Library
from typing import Union, Annotated

# Third Party
from aws_lambda_powertools import Logger
from fastapi import APIRouter, Body, status, Header
from fastapi.responses import JSONResponse

# Local Modules
from core.utils import extract_username_from_basic_auth
from api_backend.utils import get_answer_from_rag
from api_backend.models import (
    RagQueryRequest,
    RagQueryResponse,
    RagQueryErrorResponse,
)

# Initialize logger
logger = Logger(service="query")

# Initialize router for asset management
router = APIRouter(prefix="/query", tags=["Query"])


@router.post(
    "",
    response_model=Union[RagQueryResponse, RagQueryErrorResponse],
    status_code=status.HTTP_200_OK,
)
def query_endpoint(
    x_arcane_auth_token: Annotated[str, Header(...)],
    request: RagQueryRequest = Body(...),
) -> JSONResponse:
    """Query endpoint for Retrieval-Augmented Generation (RAG) queries.

    **Parameters:**
    - **x_arcane_auth_token**: str
        The authentication token for the request, typically provided in the
        `x-arcane-auth-token` header.
    - **request**: RagQueryRequest
        The request body containing the query text, SRD ID, and optional
        parameters for generative LLM configuration, including:
        - `query_text`: The text of the query to process.
        - `srd_id`: The ID of the SRD document to query against.
        - `invoke_generative_llm`: Flag to indicate if a generative LLM should be invoked.
        - `use_conversation_style`: Flag to indicate if conversational style should be used.
        - `generation_config`: Optional configuration for generation.
        - `number_of_documents`: Optional parameter to specify the number of documents to retrieve.

    **Returns:**
    - **JSONResponse**: A JSON response containing the query results or an
    error message if the request fails.
    """
    # Extract username from Basic Auth header
    owner_id = extract_username_from_basic_auth(x_arcane_auth_token)

    # Validate the owner_id
    if not owner_id:
        logger.error(
            "Invalid or missing authentication token",
            extra={"raw_body": request.model_dump_json()},
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid or missing authentication token"},
        )

    try:
        # Extract query text and SRD ID from the request body
        query_text = request.query_text.strip()
        srd_id = request.srd_id.strip()

        # Extract optional parameters for generative LLM configuration
        # Use generative LLM flag
        invoke_generative_llm = request.invoke_generative_llm or False

        # Use conversational style flag
        use_conversational_style = request.use_conversation_style or False

        # Generation config payload
        if request.generation_config is None:
            generation_config_payload = {}
        else:
            generation_config_payload = request.generation_config.model_dump(
                mode="json"
            )

    # Parsing errors
    except Exception as e:
        logger.exception(
            f"Error processing query request input: {e}",
            extra={"raw_body": request.model_dump_json()},
        )
        status_code = status.HTTP_400_BAD_REQUEST
        content = {"error": f"Malformed request: {e}"}
        return JSONResponse(status_code=status_code, content=content)

    # Create composite key
    composite_key = f"{owner_id}#{srd_id}"

    # Get the answer from the RAG processor
    try:
        logger.info(
            f"Processing query for composite key '{composite_key}': '{query_text}', "
            f"Generative: {invoke_generative_llm}"
        )
        content = get_answer_from_rag(
            query_text=query_text,
            owner_id=owner_id,
            srd_id=srd_id,
            invoke_generative_llm=invoke_generative_llm,
            use_conversational_style=use_conversational_style,
            generation_config_payload=generation_config_payload,
            number_of_documents=request.number_of_documents,
            lambda_logger=logger,
        )

        # Check if the result contains an error
        status_code = 200
        if "error" in content:
            logger.warning(
                f"Query for '{query_text}' on '{composite_key}' resulted in "
                f"error: {content['error']}"
            )
            if "Could not load SRD data" in content["error"]:
                status_code = 404
            elif "components not ready" in content["error"]:
                status_code = 503  # Service unavailable
            else:
                status_code = 500  # General internal error from processor

    # Handle specific errors from the RAG processor
    except Exception as e:
        logger.exception(
            f"Unhandled error in query_endpoint for composite key '{composite_key}': {e}"
        )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        content = {"error": f"Internal server error: {e}"}

    # Return the response
    return JSONResponse(status_code=status_code, content=content)
