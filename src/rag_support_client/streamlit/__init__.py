"""Streamlit application initialization"""

import atexit
import os
from pathlib import Path
from typing import Any, NoReturn, cast

from langchain.vectorstores import Chroma

import streamlit as st
from rag_support_client.config.config import get_settings
from rag_support_client.rag.document_loader import DocumentLoader
from rag_support_client.rag.llm.ollama import create_chain
from rag_support_client.rag.vectorstore.base import VectorStoreManager
from rag_support_client.utils.logger import logger
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.scriptrunner import StopException
from streamlit.runtime.state.session_state_proxy import SessionStateProxy

# Global variables
settings = get_settings()
_global_vectorstore: Chroma | None = None
_global_rag_chain: Any | None = None
_is_initialized: bool = False

# Type hint for Streamlit module
St = cast(DeltaGenerator, st)


def get_vectorstore() -> Chroma | None:
    """Get global vectorstore instance.

    Returns:
        Chroma | None: The global vectorstore instance or None
    """
    global _global_vectorstore
    return _global_vectorstore


def get_rag_chain() -> Any | None:
    """Get global RAG chain instance.

    Returns:
        Any | None: The global RAG chain instance or None
    """
    global _global_rag_chain
    return _global_rag_chain


def is_initialized() -> bool:
    """Check if global components are initialized.

    Returns:
        bool: True if components are initialized, False otherwise
    """
    global _is_initialized
    return _is_initialized


def create_pages_symlink() -> None:
    """Create symbolic link to pages directory."""
    source = Path(__file__).parent / "pages"
    target = Path.cwd() / "pages"

    if not target.exists():
        try:
            os.symlink(source, target, target_is_directory=True)
            logger.info(f"Created symlink from {source} to {target}")
        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")

    # Register cleanup
    atexit.register(lambda: target.unlink(missing_ok=True))


def initialize_rag_components() -> None:
    """Initialize RAG components globally."""
    global _global_vectorstore, _global_rag_chain, _is_initialized

    try:
        if not _is_initialized:
            # Load documents and create vectorstore
            loader = DocumentLoader()
            documents = loader.load_documents()
            _global_vectorstore = VectorStoreManager.create_vectorstore(documents)

            # Create RAG chain
            _global_rag_chain = create_chain(_global_vectorstore)

            _is_initialized = True
            logger.info("RAG components initialized successfully")

            # Store initialization flag in session state for UI feedback
            session_state = cast(SessionStateProxy, St.session_state)
            if "session_initialized" not in session_state:
                session_state.session_initialized = True

    except Exception as e:
        logger.error(f"Failed to initialize RAG components: {e}")
        St.error("Failed to initialize the application. Please check the logs.")


def run_app() -> NoReturn:
    """Main entry point for Streamlit application.

    Raises:
        StopException: To stop the Streamlit script
    """
    try:
        # Create symlink for pages
        create_pages_symlink()

        # Initialize global RAG components
        initialize_rag_components()

        # Initialize session-specific state
        session_state = cast(SessionStateProxy, St.session_state)
        if "messages" not in session_state:
            session_state.messages = []

        # Stop the script here - let Streamlit handle the rest
        raise StopException()

    except StopException:
        raise
    except Exception as e:
        logger.error(f"Application error: {e}")
        St.error("An error occurred. Please check the logs.")
        raise StopException() from e
