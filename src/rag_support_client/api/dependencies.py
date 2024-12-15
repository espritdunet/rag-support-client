"""
FastAPI dependencies and shared utilities.
"""

from fastapi import Header, HTTPException, status
from langchain.chains import ConversationalRetrievalChain

from rag_support_client.config.config import get_settings
from rag_support_client.utils.logger import logger
from rag_support_client.utils.state import app_state

settings = get_settings()


async def get_api_key(
    x_api_key: str = Header(None, alias=settings.API_KEY_NAME)
) -> str:
    logger.warning(f"API Key received: {x_api_key}")
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is required"
        )
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    return x_api_key


async def get_rag_chain() -> ConversationalRetrievalChain:
    if app_state.rag_chain is None:
        raise HTTPException(
            status_code=503, detail="Service not ready - RAG chain not initialized"
        )
    return app_state.rag_chain
