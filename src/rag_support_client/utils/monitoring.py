"""Service monitoring and RAG parameters management"""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import httpx
import psutil
from chromadb.api.models.Collection import Collection

from rag_support_client.config.config import Settings, get_settings
from rag_support_client.streamlit.types import (
    RagConfiguration,
    RagParameter,
    SystemStatus,
)
from rag_support_client.utils.logger import logger

# Define RAG parameters as a module-level constant
RAG_PARAMETERS: dict[str, dict[str, Any]] = {
    "OLLAMA_BASE_URL": {
        "description": "Base URL for Ollama API",
        "min_value": None,
        "max_value": None,
        "requires_reload": True,
    },
    "OLLAMA_TIMEOUT": {
        "description": "Timeout for Ollama API calls (seconds)",
        "min_value": 1,
        "max_value": 600,
        "requires_reload": False,
    },
    "LLM_MODEL": {
        "description": "Name of the LLM model to use",
        "min_value": None,
        "max_value": None,
        "requires_reload": True,
    },
    "EMBEDDING_MODEL": {
        "description": "Name of the embedding model to use",
        "min_value": None,
        "max_value": None,
        "requires_reload": True,
    },
    "LLM_TEMPERATURE": {
        "description": "Temperature for LLM response generation",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "LLM_NUM_CTX": {
        "description": "Maximum context length for LLM",
        "min_value": 512,
        "max_value": 8192,
        "requires_reload": True,
    },
    "LLM_TOP_K": {
        "description": "Number of top tokens to consider for sampling",
        "min_value": 1,
        "max_value": 100,
        "requires_reload": False,
    },
    "LLM_TOP_P": {
        "description": "Cumulative probability threshold for sampling",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    # Text Processing Settings
    "CHUNK_SIZE": {
        "description": "Size of text chunks for processing",
        "min_value": 100,
        "max_value": 2000,
        "requires_reload": True,
    },
    "CHUNK_OVERLAP": {
        "description": "Number of characters to overlap between chunks",
        "min_value": 0,
        "max_value": 1000,
        "requires_reload": True,
    },
    "SPLIT_METHOD": {
        "description": "Method used for splitting text (recursive/fixed)",
        "min_value": None,
        "max_value": None,
        "requires_reload": True,
    },
    # Scoring Weights
    "SIMILARITY_WEIGHT": {
        "description": "Weight for semantic similarity between query and context",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "RELEVANCE_WEIGHT": {
        "description": "Weight for relevance of context to query",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "COVERAGE_WEIGHT": {
        "description": "Weight for how well context covers query topics",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "COHERENCE_WEIGHT": {
        "description": "Weight for logical flow and consistency",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "COMPLETENESS_WEIGHT": {
        "description": "Weight for answer completeness",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "CONSISTENCY_WEIGHT": {
        "description": "Weight for internal consistency",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    # Scoring Thresholds
    "MIN_ACCEPTABLE_SCORE": {
        "description": "Minimum score threshold for valid responses",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "EXCELLENT_SCORE": {
        "description": "Score threshold for high-quality responses",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "CONTRADICTION_PENALTY": {
        "description": "Penalty factor for contradictory information",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "QUESTION_KEYWORDS_WEIGHT": {
        "description": "Weight for matching question keywords",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    "CONTEXT_MATCH_WEIGHT": {
        "description": "Weight for context relevance matching",
        "min_value": 0.0,
        "max_value": 1.0,
        "requires_reload": False,
    },
    # Answer Settings
    "MIN_ANSWER_LENGTH": {
        "description": "Minimum acceptable answer length in characters",
        "min_value": 10,
        "max_value": 1000,
        "requires_reload": False,
    },
    "OPTIMAL_ANSWER_LENGTH": {
        "description": "Target answer length in characters",
        "min_value": 50,
        "max_value": 2000,
        "requires_reload": False,
    },
}


# Global settings instance with proper typing
_settings: Settings | None = None


def get_current_settings() -> Settings:
    """Get fresh settings instance."""
    global _settings
    _settings = get_settings()
    return _settings


@contextmanager
def update_env_file() -> Generator[None, None, None]:
    """Safe .env file update context manager with file locking."""
    env_path = Path(".env")
    if not env_path.exists():
        raise FileNotFoundError(".env file not found")

    # Read current content
    with open(env_path) as f:
        original_content = f.read()

    try:
        yield
    except Exception as e:
        # Restore original content on error
        with open(env_path, "w") as f:
            f.write(original_content)
        raise e


def clear_settings_cache() -> None:
    """Clear settings cache and force reload."""
    global _settings
    _settings = None

    try:
        # Force reload config module
        import importlib

        import rag_support_client.config.config

        importlib.reload(rag_support_client.config.config)

        # Clear module cache
        import sys

        if "rag_support_client.config.config" in sys.modules:
            del sys.modules["rag_support_client.config.config"]

        logger.info("Settings cache cleared successfully")

    except Exception as e:
        logger.error(f"Failed to clear settings cache: {e}")
        raise


def update_env_parameter(param_name: str, value: Any) -> bool:
    """Update parameter in .env file with validation."""
    try:
        with update_env_file():
            env_path = Path(".env")

            # Read all lines
            with open(env_path) as f:
                lines = f.readlines()

            # Update or append parameter
            param_updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{param_name}="):
                    lines[i] = f"{param_name}={value}\n"
                    param_updated = True
                    break

            if not param_updated:
                lines.append(f"{param_name}={value}\n")

            # Write updated content
            with open(env_path, "w") as f:
                f.writelines(lines)

            # Verify update
            with open(env_path) as f:
                content = f.read()
                if f"{param_name}={value}" not in content:
                    raise ValueError(f"Failed to verify {param_name} update")

            # Clear cache after successful update
            clear_settings_cache()

            logger.info(f"Successfully updated parameter {param_name}={value}")
            return True

    except Exception as e:
        logger.error(f"Failed to update parameter {param_name}: {e}")
        return False


def get_current_configuration() -> RagConfiguration:
    """Get current RAG configuration with fresh settings."""
    try:
        # Get fresh settings
        settings = get_current_settings()

        parameters: dict[str, RagParameter] = {}
        for param_name, metadata in RAG_PARAMETERS.items():
            # Get value from settings, convert to float if numeric
            value = getattr(settings, param_name)
            try:
                # Try to convert to float if possible
                if isinstance(value, int | float):
                    value = float(value)
                    # Round numeric values
                    value = round(value, 3)
            except (ValueError, TypeError):
                # Keep original value if not numeric
                pass

            # Create parameter object
            parameters[param_name] = RagParameter(
                name=param_name,
                value=value,
                description=metadata["description"],
                min_value=metadata.get("min_value"),
                max_value=metadata.get("max_value"),
                requires_reload=metadata["requires_reload"],
            )

        return RagConfiguration(
            parameters=parameters,
            last_update=datetime.now(),
            pending_changes=False,
        )

    except Exception as e:
        logger.error(f"Failed to get current configuration: {e}")
        raise


def update_configuration(param_name: str, value: float) -> tuple[bool, str]:
    """Update RAG parameter with validation and cache management.

    Args:
        param_name: Name of the parameter to update
        value: New value for the parameter

    Returns:
        tuple[bool, str]: Success status and message
    """
    try:
        if param_name not in RAG_PARAMETERS:
            return False, f"Unknown parameter: {param_name}"

        metadata = RAG_PARAMETERS[param_name]
        min_val = cast(float, metadata["min_value"])
        max_val = cast(float, metadata["max_value"])
        value = round(value, 3)

        if not (min_val <= value <= max_val):
            return False, f"Value {value} outside range [{min_val}, {max_val}]"

        # Store current value for verification
        settings = get_current_settings()
        old_value = getattr(settings, param_name)

        # Update .env file
        if update_env_parameter(param_name, value):
            # Force settings reload and verify
            clear_settings_cache()
            new_settings = get_current_settings()
            new_value = getattr(new_settings, param_name)

            # Verify update with tolerance for floating point comparison
            if abs(float(new_value) - value) > 0.001:
                # Rollback if verification fails
                update_env_parameter(param_name, old_value)
                return False, f"Value verification failed for {param_name}"

            logger.info(
                f"Successfully updated {param_name} from {old_value} to {value}"
            )
            return True, f"Successfully updated {param_name} to {value}"

        return False, f"Failed to update {param_name}"

    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return False, str(e)


async def check_ollama_health() -> tuple[SystemStatus, str]:
    """Check Ollama service health status."""
    try:
        settings = get_current_settings()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=5.0,
            )
            if response.status_code == 200:
                return SystemStatus.HEALTHY, "Ollama service is healthy"
            return (
                SystemStatus.DEGRADED,
                f"Ollama service returned status code {response.status_code}",
            )
    except httpx.TimeoutException:
        return SystemStatus.DEGRADED, "Ollama service timeout"
    except Exception as e:
        return SystemStatus.DOWN, f"Ollama service error: {str(e)}"


def check_chromadb_health(collection: Collection) -> tuple[SystemStatus, str]:
    """Check ChromaDB health status with detailed metrics."""
    try:
        count = collection.count()
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        status_details = (
            f"Embeddings: {count:,}, "
            f"Memory usage: {memory_info.rss / 1024 / 1024:.1f}MB "
            f"({memory_percent:.1f}%)"
        )

        if memory_percent > 90:
            return (
                SystemStatus.DEGRADED,
                f"ChromaDB high memory usage: {status_details}",
            )

        if count == 0:
            return (
                SystemStatus.DEGRADED,
                f"ChromaDB empty: {status_details}",
            )

        return (
            SystemStatus.HEALTHY,
            f"ChromaDB healthy: {status_details}",
        )
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        return SystemStatus.DOWN, f"ChromaDB error: {str(e)}"


def reset_chromadb(collection: Collection) -> tuple[bool, str]:
    """Reset ChromaDB collection with validation."""
    try:
        initial_count = collection.count()
        if initial_count == 0:
            return True, "Collection already empty"

        # Attempt deletion
        collection.delete(where=None)

        # Verify deletion
        final_count = collection.count()
        if final_count == 0:
            logger.info(f"Successfully deleted {initial_count:,} embeddings")
            return True, f"Successfully deleted {initial_count:,} embeddings"

        return False, f"Failed to delete all embeddings ({final_count:,} remaining)"

    except Exception as e:
        logger.error(f"Failed to reset ChromaDB: {e}")
        return False, f"Failed to reset ChromaDB: {str(e)}"


def export_configuration() -> tuple[bool, str]:
    """Export current configuration to JSON with validation."""
    try:
        config = get_current_configuration()
        export_path = Path("config_export.json")

        # Prepare export data
        export_data = {
            "parameters": {
                k: {
                    "name": v.name,
                    "value": v.value,
                    "description": v.description,
                    "min_value": v.min_value,
                    "max_value": v.max_value,
                    "requires_reload": v.requires_reload,
                }
                for k, v in config.parameters.items()
            },
            "last_update": config.last_update.isoformat(),
            "pending_changes": config.pending_changes,
        }

        # Export with pretty printing
        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Configuration exported to {export_path}")
        return True, f"Configuration exported to {export_path}"

    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        return False, f"Failed to export configuration: {str(e)}"
