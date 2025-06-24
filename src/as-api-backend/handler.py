# Standard Library
import os
from typing import Dict, Any

# Third Party
from mangum import Mangum
from fastapi import FastAPI, Depends, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

# Local Modules
from api_backend import router
from api_backend.dependencies import verify_source_ip
from core.utils.config import API_PREFIX

# Initialize a logger
logger = Logger()

# Parse the CORS origins from the environment variables
allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(",")

# Create a FastAPI application instance
app = FastAPI(
    title="Arcane Scribe API",
    version="0.2.0",
    description="API for Arcane Scribe, a tool for managing and querying knowledge bases.",
    docs_url=None,  # Disable default docs URL
    redoc_url=None,  # Disable default ReDoc URL
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# Add CORS Middleware to the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# region Define custom documentation routes
docs_router = APIRouter(
    prefix=API_PREFIX,
    tags=["Documentation"],
    dependencies=[Depends(verify_source_ip)],
)


@docs_router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """Custom Swagger UI HTML endpoint.

    Returns
    -------
    HTMLResponse
        The HTML response for the Swagger UI documentation.
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,  # Use the app's openapi_url
        title=app.title + " - Swagger UI",
    )


@docs_router.get("/redoc", include_in_schema=False)
async def custom_redoc_html() -> HTMLResponse:
    """Custom ReDoc HTML endpoint.

    Returns
    -------
    HTMLResponse
        The HTML response for the ReDoc documentation.
    """
    return get_redoc_html(
        openapi_url=app.openapi_url,  # Use the app's openapi_url
        title=app.title + " - ReDoc",
    )


# endregion

# Add the API router to the FastAPI app
app.include_router(router, prefix=API_PREFIX)

# Add the documentation endpoints to the FastAPI app
app.include_router(docs_router)

# Initialize Mangum handler globally
# This instance will be reused across invocations in a warm Lambda environment.
lambda_asgi_handler = Mangum(app, lifespan="off")


@logger.inject_lambda_context(
    log_event=True, correlation_id_path=correlation_paths.API_GATEWAY_HTTP
)
def lambda_handler(
    event: Dict[str, Any], context: LambdaContext
) -> Dict[str, Any]:
    """Lambda handler function to adapt the FastAPI app for AWS Lambda.

    Parameters
    ----------
    event : Dict[str, Any]
        The event data passed to the Lambda function.
    context : LambdaContext
        The context object containing runtime information.

    Returns
    -------
    Dict[str, Any]
        The response from the FastAPI application.
    """
    # Return the response from the FastAPI application
    return lambda_asgi_handler(event, context)
