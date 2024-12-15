"""
Performance tests for the RAG pipeline.

Tests response times and resource usage under various load conditions.
"""

import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from rag_support_client.config.config import get_settings
from rag_support_client.rag.document_loader import DocumentLoader
from rag_support_client.rag.llm.ollama import create_chain
from rag_support_client.rag.vectorstore.base import VectorStoreManager
from rag_support_client.utils.logger import logger

settings = get_settings()


@pytest.fixture(scope="module")
def performance_vectorstore() -> Generator[Any, None, None]:
    """
    Create a vectorstore with sample documents for performance testing.

    Yields:
        Any: Initialized vectorstore
    """
    try:
        # Create test directory and documents
        test_dir = Path(settings.MARKDOWN_DIR)
        loader = DocumentLoader()
        documents = loader.load_documents(test_dir)

        # Initialize vectorstore with actual documents
        perf_dir = Path(settings.CHROMA_PERSIST_DIRECTORY) / "performance_test"
        vectorstore = VectorStoreManager.create_vectorstore(
            documents=documents,
            persist_directory=str(perf_dir),
            collection_name="performance_test",
        )
        yield vectorstore

    except Exception as e:
        logger.error(f"Performance vectorstore setup failed: {e}")
        pytest.skip("Performance testing environment setup failed")


@pytest.fixture(scope="module")
def performance_chain(performance_vectorstore: Any) -> Generator[Any, None, None]:
    """
    Create RAG chain for performance testing.

    Args:
        performance_vectorstore: Initialized vectorstore

    Yields:
        Any: Configured RAG chain
    """
    try:
        chain = create_chain(performance_vectorstore)
        yield chain
    except Exception as e:
        logger.error(f"Performance chain setup failed: {e}")
        pytest.skip("Performance chain setup failed")


def test_single_query_response_time(performance_chain: Any) -> None:
    """
    Test response time for a single query.

    Args:
        performance_chain: Configured RAG chain
    """
    question = "Comment configurer Yavin ?"

    start_time = time.perf_counter()
    performance_chain.invoke({"question": question})
    response_time = time.perf_counter() - start_time

    # Log performance metrics
    logger.info(f"Single query response time: {response_time:.2f} seconds")

    # Assert reasonable response time (adjust threshold as needed)
    assert response_time < 10.0, f"Response time too high: {response_time:.2f}s"


def test_multiple_queries_response_time(performance_chain: Any) -> None:
    """
    Test response time consistency across multiple queries.

    Args:
        performance_chain: Configured RAG chain
    """
    test_questions = [
        "Comment installer Yavin ?",
        "Comment configurer le réseau ?",
        "Où trouver l'adresse IP ?",
        "Comment activer l'API ?",
    ]

    response_times = []
    for question in test_questions:
        start_time = time.perf_counter()
        performance_chain.invoke({"question": question})
        response_time = time.perf_counter() - start_time
        response_times.append(response_time)

        # Allow cooldown between requests
        time.sleep(1)

    # Calculate statistics
    avg_time = sum(response_times) / len(response_times)
    max_time = max(response_times)
    min_time = min(response_times)

    # Log performance metrics
    logger.info(
        f"Multiple queries performance:\n"
        f"Average: {avg_time:.2f}s\n"
        f"Max: {max_time:.2f}s\n"
        f"Min: {min_time:.2f}s"
    )

    # Assert performance requirements
    assert avg_time < 10.0, f"Average response time too high: {avg_time:.2f}s"
    assert max_time < 15.0, f"Maximum response time too high: {max_time:.2f}s"


def test_concurrent_queries_response_time(performance_chain: Any) -> None:
    """
    Test response time under concurrent load using asyncio.

    Args:
        performance_chain: Configured RAG chain
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    async def process_concurrent_queries(num_concurrent: int = 3) -> list[float]:
        """Process multiple queries concurrently."""
        questions = [
            "Comment installer Yavin ?",
            "Comment configurer le réseau ?",
            "Où trouver l'adresse IP ?",
        ]

        async def process_query(question: str) -> float:
            """Process single query and return response time."""
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                start_time = time.perf_counter()
                await loop.run_in_executor(
                    pool, lambda: performance_chain.invoke({"question": question})
                )
                return time.perf_counter() - start_time

        # Create concurrent tasks
        tasks = [process_query(q) for q in questions[:num_concurrent]]
        response_times = await asyncio.gather(*tasks)
        return list(response_times)

    # Run concurrent test
    response_times = asyncio.run(process_concurrent_queries())

    # Calculate statistics
    avg_concurrent_time = sum(response_times) / len(response_times)
    max_concurrent_time = max(response_times)

    # Log performance metrics
    logger.info(
        f"Concurrent queries performance:\n"
        f"Average: {avg_concurrent_time:.2f}s\n"
        f"Max: {max_concurrent_time:.2f}s"
    )

    # Assert performance under concurrent load
    assert (
        avg_concurrent_time < 15.0
    ), f"Average concurrent response time too high: {avg_concurrent_time:.2f}s"
    assert (
        max_concurrent_time < 20.0
    ), f"Maximum concurrent response time too high: {max_concurrent_time:.2f}s"


def test_retrieval_performance(performance_chain: Any) -> None:
    """
    Test vector retrieval performance.

    Args:
        performance_chain: Configured RAG chain
    """
    question = "Comment configurer le réseau Yavin ?"

    start_time = time.perf_counter()
    docs = performance_chain.retriever.get_relevant_documents(question)
    retrieval_time = time.perf_counter() - start_time

    # Log retrieval metrics
    logger.info(
        f"Retrieval performance:\n"
        f"Time: {retrieval_time:.2f}s\n"
        f"Documents retrieved: {len(docs)}"
    )

    # Assert retrieval performance
    assert retrieval_time < 1.0, f"Retrieval time too high: {retrieval_time:.2f}s"
    assert len(docs) > 0, "No documents retrieved"
