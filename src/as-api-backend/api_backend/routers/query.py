# Standard Library
from typing import Union

# Third Party
from fastapi import APIRouter, Body, status, Depends
from fastapi.responses import JSONResponse
from aws_lambda_powertools import Logger

# Local Modules
from api_backend.utils import get_answer_from_rag
from api_backend.models import (
    User,
    RagQueryRequest,
    RagQueryResponse,
    RagQueryErrorResponse,
)
from api_backend.dependencies import get_current_user

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
    current_user: User = Depends(get_current_user),
    request: RagQueryRequest = Body(...),
) -> JSONResponse:
    """Query endpoint for Retrieval-Augmented Generation (RAG) queries.

    **Parameters:**
    - **current_user**: The currently authenticated user, obtained from the
      `get_current_user` dependency.
    - **request**: The request body containing the query text, SRD ID, and
      optional parameters for generative LLM configuration.

    **Returns:**
    - **JSONResponse**: A JSON response containing the query results or an
    error message if the request fails.
    """
    # Extract the username
    owner_id = current_user.username

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
