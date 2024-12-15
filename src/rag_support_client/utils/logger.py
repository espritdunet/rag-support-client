"""
Logging configuration for the RAG Support application.
Provides a centralized logging setup with both file and console handlers.
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from rag_support_client.config import settings
from rag_support_client.config.config import LogLevel


def get_log_level(level_setting: LogLevel | str) -> int:
    """Convert LogLevel enum or string to logging constant.

    Args:
        level_setting: Log level from settings

    Returns:
        int: Logging level constant
    """
    level_map = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
        LogLevel.CRITICAL: logging.CRITICAL,
    }

    # If it's already a LogLevel enum
    if isinstance(level_setting, LogLevel):
        return level_map.get(level_setting, logging.INFO)

    # If it's a string, try to convert to LogLevel
    try:
        return level_map.get(LogLevel(str(level_setting).upper()), logging.INFO)
    except ValueError:
        return logging.INFO


def setup_logging() -> logging.Logger:
    """
    Configure application-wide logging system with daily log rotation.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Ensure log directory exists
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Replace FileHandler by TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        str(log_file), when="midnight", interval=1, backupCount=30, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    # Optional : defining backup files suffix
    file_handler.suffix = "%Y-%m-%d"

    # Create application logger
    logger = logging.getLogger("rag_support")

    # Convert log level setting to logging constant
    log_level = get_log_level(settings.LOG_LEVEL)
    logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Ensure propagation is enabled
    logger.propagate = True

    # Reduce logging noise from verbose libraries
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger


logger = setup_logging()
