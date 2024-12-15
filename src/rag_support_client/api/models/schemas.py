"""
Pydantic models for API request/response validation.

This module defines the data models used for validating API requests and responses,
ensuring type safety and data consistency throughout the application.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from rag_support_client.config.config import settings


class ChatRequest(BaseModel):
    """Validates incoming chat requests."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(
        ...,
        min_length=settings.API_MIN_QUESTION_LENGTH,
        max_length=settings.API_MAX_QUESTION_LENGTH,
        description="User question",
        examples=["Comment configurer mon terminal de paiement ?"],
    )


class ConfidenceScore(BaseModel):
    """Simple confidence scoring for response quality."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    level: Literal["high", "medium", "low"] = Field(
        ..., description="Qualitative confidence level"
    )


class ChatResponse(BaseModel):
    """Structured response from the chat system."""

    model_config = ConfigDict(frozen=True)

    answer: str = Field(
        ...,
        description="Generated response",
    )
    sources: list[str] = Field(
        default_factory=list,
        max_length=settings.API_MAX_SOURCES,
        description="Source documentation URLs",
    )
    confidence: ConfidenceScore = Field(..., description="Confidence scoring")


class HealthResponse(BaseModel):
    """API health check response."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Current service status",
    )
    version: str = Field(
        ..., pattern=r"^\d+\.\d+\.\d+$", description="Semantic version"
    )
