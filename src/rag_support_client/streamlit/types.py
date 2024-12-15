"""Type definitions for Streamlit components and admin interfaces"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeAlias

from pydantic import BaseModel

from streamlit.delta_generator import DeltaGenerator  # Import
from streamlit.runtime.scriptrunner import ScriptRunContext
from streamlit.runtime.state import SessionStateProxy

# Re-export DeltaGenerator and define type aliases
__all__ = ["DeltaGenerator", "ScriptContext", "SessionState", "SystemStatus"]

# Type aliases for Streamlit
ScriptContext: TypeAlias = ScriptRunContext
SessionState: TypeAlias = SessionStateProxy


class SystemStatus(str, Enum):
    """Enum for system component status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class MemoryStats:
    """Memory statistics for a system component"""

    total: int
    used: int
    available: int
    percent_used: float
    timestamp: datetime


@dataclass
class RagMetrics(BaseModel):
    """Performance metrics for RAG system"""

    avg_response_time: float  # in seconds
    requests_per_minute: float
    ollama_latency: float  # in milliseconds
    success_rate: float  # percentage
    timestamp: datetime

    class Config:
        arbitrary_types_allowed = True


@dataclass
class DocumentStats:
    """Statistics about loaded documents"""

    total_documents: int
    total_chunks: int
    avg_chunk_size: float
    last_update: datetime


class RagParameter(BaseModel):
    """Model for RAG parameter configuration."""

    name: str
    value: Any
    description: str
    min_value: float | None = None
    max_value: float | None = None
    requires_reload: bool = False


class RagConfiguration(BaseModel):
    """Current RAG system configuration"""

    parameters: dict[str, RagParameter]
    last_update: datetime
    pending_changes: bool = False
