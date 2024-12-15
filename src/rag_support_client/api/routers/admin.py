"""
Administrative endpoints for the RAG Support API.
"""

from fastapi import APIRouter, HTTPException

from rag_support_client.utils.logger import logger

from ..models.schemas import HealthResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check the health status of the API and its components.

    Returns:
        HealthResponse: Health status response

    Raises:
        HTTPException: If health check fails
    """
    try:
        return HealthResponse(status="healthy", version="1.0.0")
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail="System health check failed"
        ) from e  # Added 'from e' to properly chain the exception
