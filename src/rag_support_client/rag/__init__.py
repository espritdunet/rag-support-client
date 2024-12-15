# src/rag_support_client/rag/__init__.py
"""
RAG module initialization.
Provides access to main RAG components.
"""
from .embeddings.ollama import get_embeddings
from .llm.ollama import create_chain
from .vectorstore.base import VectorStoreManager

__all__ = ["VectorStoreManager", "get_embeddings", "create_chain"]
