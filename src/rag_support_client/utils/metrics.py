"""Metrics collection and monitoring for RAG system"""

import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar, cast

import httpx
import psutil
from chromadb.api.models.Collection import Collection

from rag_support_client.config.config import get_settings
from rag_support_client.streamlit.types import (
    ChromaDBStatus,
    DocumentStats,
    MemoryStats,
    OllamaStatus,
    RagMetrics,
    SystemMetrics,
    SystemStatus,
)
from rag_support_client.utils.logger import logger

settings = get_settings()

# Type variables for generic function signatures
T = TypeVar("T")
P = TypeVar("P")

# Global metrics storage
_request_times: list[float] = []
_requests_last_minute: list[float] = []
_ollama_latencies: list[float] = []
_last_errors: list[str] = []


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure function execution time"""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            _request_times.append(duration)
            _requests_last_minute.append(time.time())
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            _request_times.append(duration)
            _requests_last_minute.append(time.time())
            _last_errors.append(f"{datetime.now()}: {str(e)}")
            raise

    return wrapper


def measure_time_async(
    func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T]]:
    """Decorator to measure async function execution time"""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            _request_times.append(duration)
            _requests_last_minute.append(time.time())
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            _request_times.append(duration)
            _requests_last_minute.append(time.time())
            _last_errors.append(f"{datetime.now()}: {str(e)}")
            raise

    return wrapper


def _clean_old_metrics() -> None:
    """Clean up metrics older than 1 hour"""
    current_time = time.time()
    cutoff_time = current_time - 3600  # 1 hour ago

    # Clean request times
    global _request_times, _requests_last_minute, _ollama_latencies, _last_errors
    _request_times = [t for t in _request_times if t > cutoff_time]
    _requests_last_minute = [
        t for t in _requests_last_minute if t > (current_time - 60)
    ]
    _ollama_latencies = [t for t in _ollama_latencies if t > cutoff_time]

    # Keep only last hour of errors
    _last_errors = _last_errors[-100:]  # Keep last 100 errors maximum


async def check_ollama_status() -> OllamaStatus:
    """Check Ollama service status and latency"""
    try:
        async with httpx.AsyncClient() as client:
            start_time = time.perf_counter()
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            latency = (time.perf_counter() - start_time) * 1000  # Convert to ms

            _ollama_latencies.append(latency)

            if response.status_code == 200:
                models = response.json()
                model_loaded = any(
                    model["name"] == settings.LLM_MODEL
                    for model in models.get("models", [])
                )
                return OllamaStatus(
                    status=SystemStatus.HEALTHY,
                    model_loaded=model_loaded,
                    api_latency=latency,
                    timestamp=datetime.now(),
                )
            return OllamaStatus(
                status=SystemStatus.DEGRADED,
                model_loaded=False,
                api_latency=latency,
                timestamp=datetime.now(),
            )
    except Exception as e:
        logger.error(f"Failed to check Ollama status: {e}")
        return OllamaStatus(
            status=SystemStatus.DOWN,
            model_loaded=False,
            api_latency=0.0,
            timestamp=datetime.now(),
        )


def get_chromadb_status(collection: Collection) -> ChromaDBStatus:
    """Get ChromaDB status and metrics"""
    try:
        # Get collection stats
        count = collection.count()

        # Get memory stats for the ChromaDB process
        process = psutil.Process()
        mem_info = process.memory_info()

        memory_stats = MemoryStats(
            total=mem_info.rss + mem_info.vms,
            used=mem_info.rss,
            available=psutil.virtual_memory().available,
            percent_used=process.memory_percent(),
            timestamp=datetime.now(),
        )

        return ChromaDBStatus(
            status=SystemStatus.HEALTHY,
            collection_count=1,  # We only use one collection
            total_embeddings=count,
            memory_stats=memory_stats,
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error(f"Failed to get ChromaDB status: {e}")
        return ChromaDBStatus(
            status=SystemStatus.DOWN,
            collection_count=0,
            total_embeddings=0,
            memory_stats=MemoryStats(
                total=0,
                used=0,
                available=0,
                percent_used=0.0,
                timestamp=datetime.now(),
            ),
            timestamp=datetime.now(),
        )


def calculate_rag_metrics() -> RagMetrics:
    """Calculate current RAG system metrics"""
    _clean_old_metrics()

    # Calculate average response time
    avg_response_time = (
        sum(_request_times) / len(_request_times) if _request_times else 0.0
    )

    # Calculate requests per minute
    requests_per_minute = len(_requests_last_minute)

    # Calculate average Ollama latency
    avg_ollama_latency = (
        sum(_ollama_latencies) / len(_ollama_latencies) if _ollama_latencies else 0.0
    )

    # Calculate success rate
    total_requests = len(_request_times)
    error_count = len(_last_errors)
    success_rate = (
        ((total_requests - error_count) / total_requests) * 100
        if total_requests > 0
        else 100.0
    )

    return RagMetrics(
        avg_response_time=avg_response_time,
        requests_per_minute=float(requests_per_minute),
        ollama_latency=avg_ollama_latency,
        success_rate=success_rate,
        timestamp=datetime.now(),
    )


async def get_system_metrics(collection: Collection) -> SystemMetrics:
    """Get complete system metrics"""
    ollama_status = await check_ollama_status()
    chromadb_status = get_chromadb_status(collection)
    rag_metrics = calculate_rag_metrics()

    # Count actual documents (before chunking)
    raw_docs_path = Path(settings.RAW_DIR)
    total_documents = len(list(raw_docs_path.glob("**/*.md")))

    # Get chunks count from ChromaDB
    total_chunks = collection.count()

    # Calculate average chunk size if there are chunks
    avg_chunk_size = float(settings.CHUNK_SIZE)  # default value
    if total_chunks > 0:
        try:
            # Get a sample of chunks to calculate average size
            sample = collection.get(limit=min(total_chunks, 100))
            if sample and isinstance(sample, dict) and "documents" in sample:
                docs = cast(list[str], sample["documents"])
                if docs:
                    total_chars = sum(len(doc) for doc in docs)
                    avg_chunk_size = float(total_chars / len(docs))
        except Exception as e:
            logger.warning(f"Failed to calculate average chunk size: {e}")

    # Create document stats
    docs_stats = DocumentStats(
        total_documents=total_documents,
        total_chunks=total_chunks,
        avg_chunk_size=avg_chunk_size,
        file_types={"md": total_documents},  # Assuming all are markdown files
        last_update=datetime.now(),
    )

    return SystemMetrics(
        ollama=ollama_status,
        chromadb=chromadb_status,
        rag_metrics=rag_metrics,
        docs_stats=docs_stats,
        errors_last_hour=_last_errors[-10:],  # Return last 10 errors
        timestamp=datetime.now(),
    )
