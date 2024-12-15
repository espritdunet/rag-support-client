# src/rag_support_client/config/config.py
"""
Configuration management module using Pydantic.
"""
import json
import logging
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# Enums for validated string choices
class Environment(str, Enum):
    """Valid environment options."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


class SplitMethod(str, Enum):
    """Valid text splitting methods."""

    RECURSIVE = "recursive"
    FIXED = "fixed"


class RetrievalType(str, Enum):
    """Valid retrieval types."""

    SIMILARITY = "similarity"
    MMR = "mmr"


class DistanceMetric(str, Enum):
    """Valid distance metrics for embeddings."""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    MANHATTAN = "manhattan"


class LogLevel(str, Enum):
    """Valid logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ConversationSettings(BaseModel):
    """Settings for conversation management."""

    max_history: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of messages to keep in conversation history",
    )
    session_timeout: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Session timeout in seconds (min 5 minutes, max 24 hours)",
    )


class MarkdownSettings(BaseModel):
    """Settings for Markdown processing."""

    headers_to_split_on: list[tuple[str, str]] = Field(
        default=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        description="List of header levels to split on",
    )
    strip_headers: bool = Field(
        default=False, description="Whether to remove headers from the final chunks"
    )
    return_each_line: bool = Field(
        default=False, description="Whether to return each line as a separate chunk"
    )


class TextSplitterSettings(BaseModel):
    """Settings for text splitting configuration."""

    chunk_size: int = Field(default=1000, ge=100, le=8192)
    chunk_overlap: int = Field(default=200, ge=0)
    separators: list[str] = Field(default=["\n\n", "\n", " ", ""])
    strip_whitespace: bool = Field(default=True)
    keep_separator: bool = Field(default=True)

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, value: int, info: ValidationInfo) -> int:
        """Ensure chunk overlap is smaller than chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if value >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return value


class Settings(BaseSettings):
    """Application settings with enhanced validation."""

    # Application Settings
    APP_NAME: str = Field(default="RAG Support Client")
    APP_VERSION: str = Field(default="1.0.0")
    ENV: Environment = Field(default=Environment.DEVELOPMENT)
    DEBUG: bool = Field(default=True)

    # API Server Configuration
    HOST: str = Field(default="localhost")
    PORT: int = Field(default=8000, ge=1024, le=65535)
    API_V1_PREFIX: str = Field(default="/api/v1")
    API_MAX_QUESTION_LENGTH: int = 1000
    API_MIN_QUESTION_LENGTH: int = 3
    API_MAX_ANSWER_LENGTH: int = 8000
    API_MAX_SOURCES: int = 10
    API_MAX_CONTRADICTIONS: int = 5

    # API Security Settings
    API_KEY_NAME: str = Field(
        default="X-API-Key",
        description="Name of the header field for API key authentication",
    )
    API_KEY: str = Field(
        default="",
        min_length=32,
        description="Secret API key for authentication",
        pattern="^[a-zA-Z0-9_-]+$",
    )

    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", pattern="^https?://.*$"
    )
    OLLAMA_TIMEOUT: int = Field(default=120, ge=1, le=600)
    LLM_MODEL: str = Field(default="llama3.1:latest")
    EMBEDDING_MODEL: str = Field(default="nomic-embed-text")
    LLM_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=1.0)

    # Directory Settings
    DATA_DIR: Path = Field(default=Path("./data"))
    RAW_DIR: Path = Field(default=Path("./data/raw"))
    PROCESSED_DIR: Path = Field(default=Path("./data/processed"))
    MARKDOWN_DIR: Path = Field(default=Path("./data/raw"))

    # Text Processing Settings
    CHUNK_SIZE: int = Field(default=1000, ge=100, le=8192)
    CHUNK_OVERLAP: int = Field(default=200, ge=0)
    SPLIT_METHOD: SplitMethod = Field(default=SplitMethod.RECURSIVE)
    SEPARATORS: str = Field(
        default='["\\n\\n", "\\n", " ", ""]',
        description="JSON string of text separators",
    )

    # Vector Store Settings
    CHROMA_PERSIST_DIRECTORY: Path = Field(default=Path("./data/vector_store"))
    CHROMA_COLLECTION_NAME: str = Field(default="support_docs")
    CHROMA_ALLOW_RESET: bool = Field(default=True)
    EMBEDDING_DISTANCE_METRIC: DistanceMetric = Field(default=DistanceMetric.COSINE)

    # RAG Settings
    SIMILARITY_TOP_K: int = Field(default=3, ge=1, le=20)
    RETRIEVAL_FETCH_K: int = Field(default=6, ge=1, le=50)
    RETRIEVAL_TYPE: RetrievalType = Field(default=RetrievalType.SIMILARITY)
    SIMILARITY_THRESHOLD: float = Field(default=0.5, ge=0.0, le=1.0)

    # Scoring Settings
    SIMILARITY_WEIGHT: float = Field(default=0.3, ge=0.0, le=1.0)
    RELEVANCE_WEIGHT: float = Field(default=0.2, ge=0.0, le=1.0)
    COVERAGE_WEIGHT: float = Field(default=0.1, ge=0.0, le=1.0)
    COHERENCE_WEIGHT: float = Field(default=0.2, ge=0.0, le=1.0)
    COMPLETENESS_WEIGHT: float = Field(default=0.1, ge=0.0, le=1.0)
    CONSISTENCY_WEIGHT: float = Field(default=0.1, ge=0.0, le=1.0)

    # Scoring Thresholds
    MIN_ACCEPTABLE_SCORE: float = Field(default=0.4, ge=0.0, le=1.0)
    EXCELLENT_SCORE: float = Field(default=0.8, ge=0.0, le=1.0)

    # Advanced Scoring Settings
    CONTRADICTION_PENALTY: float = Field(default=0.3, ge=0.0, le=1.0)
    QUESTION_KEYWORDS_WEIGHT: float = Field(default=0.6, ge=0.0, le=1.0)
    CONTEXT_MATCH_WEIGHT: float = Field(default=0.4, ge=0.0, le=1.0)
    MIN_ANSWER_LENGTH: int = Field(default=50, ge=0)
    OPTIMAL_ANSWER_LENGTH: int = Field(default=200, ge=0)

    # LLM Settings
    LLM_NUM_CTX: int = Field(default=4096, ge=512, le=32768)
    LLM_TOP_K: int = Field(default=10, ge=1, le=100)
    LLM_TOP_P: float = Field(default=0.9, ge=0.0, le=1.0)
    LLM_STOP_SEQUENCES: str = Field(default="\nHuman:,\nAssistant:")
    LLM_SEED: int = Field(default=42, description="Seed for LLM response consistency")
    LLM_JSON_SYSTEM_PROMPT: str = Field(
        default="You are a technical support assistant."
        "Format ALL responses as valid JSON with this structure:"
        '{ "title": "Clear procedure title", "steps":'
        '[ { "step_number": number, "description":'
        '"What to do", "interface_elements": "UI elements to use" } ] }',
        description="System prompt for JSON formatted responses",
    )

    # Support Settings
    SUPPORT_BASE_URL: str = Field(
        default="https://support.mywebsite.com/", pattern="^https?://.*/?$"
    )

    # Logging Settings
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO)
    LOG_FILE: Path = Field(default=Path("./logs/app.log"))
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Template Settings with defaults from .env
    RAG_SYSTEM_TEMPLATE: str = Field(
        default="",  # Will be loaded from .env
        description="System prompt template for RAG interactions",
    )

    DOCUMENT_FUSION_TEMPLATE: str = Field(
        default="",  # Will be loaded from .env
        description="Template for combining document contents with user query",
    )

    QUERY_PROMPT_TEMPLATE: str = Field(
        default="",  # Will be loaded from .env
        description="Template for formatting user queries",
    )

    ERROR_RESPONSE_TEMPLATE: str = Field(
        default="",  # Will be loaded from .env
        description="Template for error responses",
    )

    @field_validator("SUPPORT_BASE_URL")
    @classmethod
    def validate_support_url(cls, value: str) -> str:
        """Ensure support URL ends with a trailing slash."""
        return value if value.endswith("/") else f"{value}/"

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Ensure API key is set and meets security requirements."""
        if not v:
            raise ValueError("API_KEY must be set in production environment")
        if len(v) < 32:
            raise ValueError("API_KEY must be at least 32 characters long")
        return v

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Validate security-related settings based on environment."""
        if self.ENV == Environment.PRODUCTION:
            if not self.API_KEY:
                raise ValueError("API_KEY must be set in production environment")
            if len(self.API_KEY) < 32:
                raise ValueError("API_KEY must be at least 32 characters in production")
        return self

    @property
    def text_splitter_settings(self) -> TextSplitterSettings:
        """Get text splitter settings as a validated object."""
        return TextSplitterSettings(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=self.text_separators,
        )

    @property
    def text_separators(self) -> list[str]:
        """
        Parse text separators from environment settings with enhanced error handling.
        Supports multiple input formats: JSON array, comma-separated string, or Python
        list.
        Falls back to default separators if parsing fails.

        Returns:
            list[str]: List of separator strings for text splitting
        """
        import logging

        default_separators = ["\n\n", "\n", ".", " ", ""]
        try:
            if not self.SEPARATORS:
                return default_separators

            # Handle native list type
            if isinstance(self.SEPARATORS, list):
                return self.SEPARATORS

            # Attempt JSON parsing with quote normalization
            try:
                parsed = json.loads(self.SEPARATORS.replace("'", '"'))
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

            # Fallback to comma-separated string parsing
            if isinstance(self.SEPARATORS, str):
                seps = [
                    s.strip()
                    .replace("\\n", "\n")
                    .replace("\\'", "'")
                    .replace('\\"', '"')
                    for s in self.SEPARATORS.strip("[]").split(",")
                    if s.strip()
                ]
                return seps if seps else default_separators

            return default_separators

        except Exception as e:
            logging.warning(f"Failed to parse SEPARATORS: {e}, using defaults")
            return default_separators

    @property
    def separators(self) -> list[str]:
        """Alias for text_separators for backward compatibility."""
        return self.text_separators

    @property
    def stop_sequences(self) -> list[str]:
        """Parse and return stop sequences as a list."""
        if not self.LLM_STOP_SEQUENCES:
            return ["\nHuman:", "\nAssistant:"]

        if isinstance(self.LLM_STOP_SEQUENCES, str):
            return [
                seq.strip() for seq in self.LLM_STOP_SEQUENCES.split(",") if seq.strip()
            ]

        return list(self.LLM_STOP_SEQUENCES)

    @property
    def templates(self) -> dict[str, str]:
        """Return a dictionary of all templates for easy access."""
        return {
            "rag_system": self.RAG_SYSTEM_TEMPLATE,
            "document_fusion": self.DOCUMENT_FUSION_TEMPLATE,
            "query": self.QUERY_PROMPT_TEMPLATE,
            "error": self.ERROR_RESPONSE_TEMPLATE,
        }

    @model_validator(mode="after")
    def validate_templates(self) -> "Settings":
        """Validate that all required template variables are present."""
        # Clean and validate RAG_SYSTEM_TEMPLATE
        if not self.RAG_SYSTEM_TEMPLATE or len(self.RAG_SYSTEM_TEMPLATE.strip()) == 0:
            raise ValueError("RAG_SYSTEM_TEMPLATE cannot be empty")

        # Clean and validate DOCUMENT_FUSION_TEMPLATE
        if not self.DOCUMENT_FUSION_TEMPLATE:
            raise ValueError("DOCUMENT_FUSION_TEMPLATE cannot be empty")
        if "{context}" not in self.DOCUMENT_FUSION_TEMPLATE:
            raise ValueError("DOCUMENT_FUSION_TEMPLATE must contain {context}")
        if "{question}" not in self.DOCUMENT_FUSION_TEMPLATE:
            raise ValueError("DOCUMENT_FUSION_TEMPLATE must contain {question}")

        # Clean and validate QUERY_PROMPT_TEMPLATE
        if not self.QUERY_PROMPT_TEMPLATE:
            raise ValueError("QUERY_PROMPT_TEMPLATE cannot be empty")
        if "{question}" not in self.QUERY_PROMPT_TEMPLATE:
            raise ValueError("QUERY_PROMPT_TEMPLATE must contain {question}")

        # Clean and validate ERROR_RESPONSE_TEMPLATE
        if not self.ERROR_RESPONSE_TEMPLATE:
            raise ValueError("ERROR_RESPONSE_TEMPLATE cannot be empty")
        if "{error_message}" not in self.ERROR_RESPONSE_TEMPLATE:
            raise ValueError("ERROR_RESPONSE_TEMPLATE must contain {error_message}")

        return self

    @model_validator(mode="after")
    def create_directories(self) -> "Settings":
        """Ensure all required directories exist."""
        dirs = [
            self.DATA_DIR,
            self.RAW_DIR,
            self.PROCESSED_DIR,
            self.MARKDOWN_DIR,
            self.CHROMA_PERSIST_DIRECTORY,
            self.LOG_FILE.parent,
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        validate_default=True,
        frozen=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Create and cache settings instance."""
    try:
        settings = Settings()
        if settings.DEBUG:
            logging.debug(f"Settings loaded successfully: {settings.model_dump()}")
        return settings
    except ValidationError as e:
        logging.error(f"Settings validation error: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading settings: {e}")
        raise


def reload_settings() -> Settings:
    """
    Force reload of settings by clearing the cache.

    Returns:
        Settings: Fresh settings instance
    """
    try:
        get_settings.cache_clear()
        global settings
        settings = get_settings()
        logging.info("Settings reloaded successfully")
        return settings
    except Exception as e:
        logging.error(f"Failed to reload settings: {str(e)}")
        raise


# Global settings Singleton instance
settings = get_settings()
