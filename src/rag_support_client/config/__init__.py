"""
Configuration package for RAG support application.
Provides centralized access to all configuration settings.
"""

from rag_support_client.config.config import get_settings, settings

__all__ = ["settings", "get_settings"]
