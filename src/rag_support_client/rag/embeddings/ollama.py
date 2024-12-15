"""
Embeddings module for the RAG Support application.
Handles embeddings configuration using LangChain v0.3.
"""

from typing import Any

from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel, Field

from rag_support_client.config.config import get_settings
from rag_support_client.utils.logger import logger

settings = get_settings()


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration with Pydantic validation."""

    model: str = Field(description="Name of the embedding model")
    base_url: str = Field(description="Base URL for Ollama API")
    client_kwargs: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        frozen = True


def get_embeddings(
    model_name: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> OllamaEmbeddings:
    """
    Create and configure cached Ollama embeddings instance.

    Args:
        model_name: Optional model name override
        base_url: Optional base URL override
        **kwargs: Additional configuration parameters for OllamaEmbeddings

    Returns:
        OllamaEmbeddings: The configured embeddings instance

    Raises:
        ValueError: If configuration validation fails
        Exception: If embeddings initialization fails
    """
    try:
        config = EmbeddingsConfig(
            model=model_name or settings.EMBEDDING_MODEL,
            base_url=base_url or settings.OLLAMA_BASE_URL,
        )

        embeddings_config = {
            "model": config.model,
            "base_url": config.base_url,
            **kwargs,
        }

        embeddings = OllamaEmbeddings(**embeddings_config)
        logger.info(f"Initialized embeddings model: {config.model}")
        return embeddings

    except Exception as e:
        logger.error(f"Embeddings initialization error: {str(e)}")
        raise
