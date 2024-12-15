"""
Integration tests for the RAG pipeline.

Tests the complete flow from document loading to response generation,
validating interactions between components.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from langchain.schema import Document

from rag_support_client.config.config import get_settings
from rag_support_client.rag.document_loader import DocumentLoader
from rag_support_client.rag.llm.ollama import create_chain
from rag_support_client.rag.vectorstore.base import VectorStoreManager
from rag_support_client.utils.logger import logger

settings = get_settings()


@pytest.fixture(scope="module")
def test_documents(tmp_path_factory: Any) -> Generator[list[Document], None, None]:
    """
    Create test documents for the complete RAG pipeline.

    Args:
        tmp_path_factory: Pytest fixture factory for temporary directories

    Yields:
        list[Document]: List of processed test documents
    """
    # Create test directory
    test_dir = tmp_path_factory.mktemp("test_docs")

    test_file = test_dir / "test_support.md"
    content = """# Configuration Yavin

## Installation
1. Installer l'application Yavin
2. Lancer l'application
3. Aller dans les réglages

## Configuration réseau
1. Activer l'API Réseau
2. Noter l'adresse IP
3. Configurer le routeur

<https://doc.yavin.com/setup>"""

    test_file.write_text(content)
    loader = DocumentLoader()
    documents = loader.load_documents(test_dir)

    yield documents


@pytest.fixture(scope="module")
def vectorstore(test_documents: list[Document]) -> Any:
    """
    Create vectorstore with test documents.

    Args:
        test_documents: List of test documents

    Returns:
        Any: Initialized vectorstore for testing
    """
    try:
        vectorstore = VectorStoreManager.create_vectorstore(
            documents=test_documents,
            persist_directory=str(Path(settings.CHROMA_PERSIST_DIRECTORY) / "test"),
            collection_name="test_collection",
        )
        return vectorstore
    except Exception as e:
        logger.error(f"Failed to create vectorstore: {e}")
        pytest.skip("Vectorstore creation failed")


@pytest.fixture(scope="module")
def rag_chain(vectorstore: Any) -> Any:
    """
    Create RAG chain with test vectorstore.

    Args:
        vectorstore: Initialized vectorstore

    Returns:
        Any: Configured RAG chain for testing
    """
    try:
        chain = create_chain(vectorstore)
        return chain
    except Exception as e:
        logger.error(f"Failed to create RAG chain: {e}")
        pytest.skip("RAG chain creation failed")


def test_document_loading(test_documents: list[Document]) -> None:
    """Test document loading and processing."""
    assert test_documents, "Should have loaded test documents"
    assert all(isinstance(doc, Document) for doc in test_documents)
    assert all("source_url" in doc.metadata for doc in test_documents)


def test_vectorstore_creation(vectorstore: Any) -> None:
    """Test vectorstore initialization."""
    assert vectorstore is not None, "Vectorstore should be created"
    assert vectorstore._collection is not None, "Collection should be initialized"
    assert vectorstore._collection.count() > 0, "Collection should contain documents"


def test_rag_chain_creation(rag_chain: Any) -> None:
    """Test RAG chain initialization."""
    assert rag_chain is not None, "RAG chain should be created"
    assert hasattr(rag_chain, "result"), "Missing result handler"


def test_rag_chain_response(rag_chain: Any) -> None:
    """Test end-to-end RAG response generation."""
    question = "Comment installer Yavin ?"

    try:
        # Get response from new LangChain 0.3 chain
        result = rag_chain.invoke({"question": question})

        # Extract response from result structure
        response = result.get("result", {}).get("response", "")

        # Validate response content
        assert response, "Should receive non-empty response"
        assert "installer" in response.lower(), "Response should be relevant"
        assert "yavin" in response.lower(), "Response should mention Yavin"

    except Exception as e:
        logger.error(f"RAG chain response error: {e}")
        pytest.fail(f"RAG chain response failed: {e}")


def test_retrieval_relevance(vectorstore: Any) -> None:
    """Test relevance of retrieved documents."""
    question = "Comment configurer le réseau Yavin ?"

    try:
        # Use vectorstore directly for retrieval test
        docs = vectorstore.similarity_search(question, k=settings.SIMILARITY_TOP_K)

        # Validate retrievals
        assert docs, "Should retrieve documents"
        assert any(
            "réseau" in doc.page_content.lower() for doc in docs
        ), "Should retrieve relevant content"

    except Exception as e:
        logger.error(f"Retrieval test error: {e}")
        pytest.fail(f"Retrieval test failed: {e}")
