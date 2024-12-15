"""
Pytest configuration and fixtures.
"""

import os
from pathlib import Path
from typing import List

import pytest
from langchain.docstore.document import Document

from rag_support_client.config.config import get_settings
from rag_support_client.rag.document_loader import DocumentLoader
from rag_support_client.rag.vectorstore.base import VectorStoreManager

settings = get_settings()


@pytest.fixture
def test_documents() -> list[Document]:
    """
    Fixture that provides test documents.
    """
    return [
        Document(
            page_content="Test document content 1", metadata={"source": "test1.txt"}
        ),
        Document(
            page_content="Test document content 2", metadata={"source": "test2.txt"}
        ),
    ]


@pytest.fixture
def vectorstore(test_documents):
    """
    Fixture that provides a test vector store.
    """
    # Create temporary test directory
    test_persist_dir = Path("./data/test_vector_store")
    test_persist_dir.mkdir(parents=True, exist_ok=True)

    # Create vector store
    vs = VectorStoreManager.create_vectorstore(
        documents=test_documents,
        persist_directory=str(test_persist_dir),
        collection_name="test_collection",
    )

    yield vs

    # Cleanup
    import shutil

    shutil.rmtree(test_persist_dir)
