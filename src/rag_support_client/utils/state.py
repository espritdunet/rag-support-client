"""
Global application state management.

This module provides a centralized state management system for the application,
handling RAG components, conversation management.

Example:
    from .state import app_state

    # Access conversation manager
    session_id = app_state.conversation_manager.create_session_id()

    # Access RAG components
    chain = app_state.rag_chain
"""

from langchain.chains import ConversationalRetrievalChain
from langchain_chroma import Chroma

from rag_support_client.config.config import get_settings

from .conversation import ConversationManager

settings = get_settings()


class AppState:
    """Global application state container with singleton pattern."""

    _instance = None

    def __new__(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.rag_chain = None
            cls._instance.vectorstore = None
            cls._instance.conversation_manager = ConversationManager()
        return cls._instance

    def __init__(self) -> None:
        self.rag_chain: ConversationalRetrievalChain | None = None
        self.vectorstore: Chroma | None = None
        self.conversation_manager: ConversationManager

    def reset(self) -> None:
        """Reset application state."""
        self.rag_chain = None
        self.vectorstore = None
        self.conversation_manager = ConversationManager()


# Global singleton instance
app_state = AppState()
