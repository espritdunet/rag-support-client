"""
Main entry point for the RAG Support application.

This module initializes and configures the FastAPI application, sets up middleware,
and manages the application lifecycle including RAG components initialization.

Returns:
    FastAPI: Configured FastAPI application instance
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from rag_support_client.api.routers import admin, chat
from rag_support_client.config.config import get_settings
from rag_support_client.rag.document_loader import DocumentLoader
from rag_support_client.rag.llm.ollama import create_chain
from rag_support_client.rag.vectorstore.base import VectorStoreManager
from rag_support_client.utils.logger import logger
from rag_support_client.utils.state import app_state

settings = get_settings()


async def custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: FastAPI request object
        exc: Caught exception

    Returns:
        JSONResponse with error details
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


def get_custom_openapi(fastapi_app: FastAPI) -> dict[str, Any]:
    """
    Customize OpenAPI schema for Swagger documentation.
    """
    if fastapi_app.openapi_schema:
        return fastapi_app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
        RAG-based customer support API

        ## Authentication
        All endpoints require API key authentication via X-API-Key header

        ## Rate Limiting
        - 100 requests per minute for chat endpoints
        - 10 requests per minute for admin endpoints
        """,
        routes=fastapi_app.routes,
        servers=[{"url": f"http://{settings.HOST}:{settings.PORT}"}],
    )

    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": settings.API_KEY_NAME}
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    # Store the schema
    fastapi_app.openapi_schema = openapi_schema
    return openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle application lifecycle events including RAG components initialization.

    Args:
        app: FastAPI application instance

    Yields:
        None: Control flow for the lifespan context

    Raises:
        RuntimeError: If critical components fail to initialize
    """
    try:
        logger.info("Application startup - Initializing RAG components")

        # Load documents
        logger.info("Loading documents...")
        loader = DocumentLoader()
        documents = loader.load_documents()
        if not documents:
            raise RuntimeError("No documents loaded")
        logger.info(f"Loaded {len(documents)} document chunks")

        # Initialize vector store
        logger.info("Initializing vector store...")
        vectorstore = VectorStoreManager.create_vectorstore(documents)
        if not vectorstore:
            raise RuntimeError("Vector store initialization failed")
        app_state.vectorstore = vectorstore

        # Initialize RAG chain
        logger.info("Creating RAG chain...")
        chain = create_chain(vectorstore)
        if not chain:
            raise RuntimeError("RAG chain initialization failed")
        app_state.rag_chain = chain

        yield
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Shutting down application...")
        if app_state.vectorstore is not None:
            try:
                # Try different cleanup methods
                for method in ["aclose", "close", "_client.close"]:
                    if hasattr(app_state.vectorstore, method):
                        await getattr(app_state.vectorstore, method)()
                        break
            except Exception as e:
                logger.warning(f"Error during vectorstore cleanup: {e}")


def create_app() -> FastAPI:
    """
    Initialize and configure the FastAPI application.
    """

    def custom_openapi() -> dict[str, Any]:
        """Generate custom OpenAPI schema."""
        if app.openapi_schema:
            return app.openapi_schema
        return get_custom_openapi(app)

    class CustomFastAPI(FastAPI):
        """Custom FastAPI class with overridden openapi method."""

        def openapi(self) -> dict[str, Any]:
            return custom_openapi()

    app = CustomFastAPI(
        title=settings.APP_NAME,
        description="API for RAG-based customer support system",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "tryItOutEnabled": True,
            "syntaxHighlight.theme": "monokai",
        },
    )

    # Include routers first
    app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["chat"])
    app.include_router(admin.router, prefix=settings.API_V1_PREFIX, tags=["admin"])

    # Exception handler
    app.add_exception_handler(Exception, custom_exception_handler)

    # Security middleware
    allowed_hosts = ["localhost", "127.0.0.1"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # CORS middleware
    allowed_origins = ["http://localhost:3000", "http://localhost:8501"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        max_age=86400,
    )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=settings.DEBUG,
    )
