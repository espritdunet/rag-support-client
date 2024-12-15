"""
Security utilities for the RAG Support API.
Implements rate limiting and input validation.
"""

import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

from rag_support_client.utils.logger import logger


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    max_requests: int = 100  # Maximum number of requests
    window_seconds: int = 60  # Time window in seconds
    block_duration: int = 300  # Block duration in seconds if limit exceeded


class RateLimiter:
    """
    Implements sliding window rate limiting.
    Tracks requests per IP address.
    """

    def __init__(self, config: RateLimitConfig = RateLimitConfig()):
        self.config = config
        self.requests: Dict[str, list[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked."""
        if ip in self.blocked_ips:
            block_time = self.blocked_ips[ip]
            if datetime.now() - block_time < timedelta(
                seconds=self.config.block_duration
            ):
                return True
            # Block duration expired, remove IP from blocked list
            del self.blocked_ips[ip]
        return False

    def add_request(self, ip: str) -> bool:
        """
        Add a request for an IP address.
        Returns False if rate limit exceeded.
        """
        if self.is_blocked(ip):
            return False

        now = datetime.now()
        window_start = now - timedelta(seconds=self.config.window_seconds)

        # Create or update request list for IP
        if ip not in self.requests:
            self.requests[ip] = []

        # Remove old requests outside window
        self.requests[ip] = [t for t in self.requests[ip] if t > window_start]

        # Check if limit exceeded
        if len(self.requests[ip]) >= self.config.max_requests:
            self.blocked_ips[ip] = now
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return False

        # Add new request
        self.requests[ip].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to apply rate limiting to API endpoints.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request: Optional[Request] = None

        # Find request object in args or kwargs
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if not request and "request" in kwargs:
            request = kwargs["request"]

        if not request:
            logger.error("No request object found for rate limiting")
            return await func(*args, **kwargs)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not rate_limiter.add_request(client_ip):
            raise HTTPException(
                status_code=429, detail="Too many requests. Please try again later."
            )

        return await func(*args, **kwargs)

    return wrapper


def validate_input_length(text: str, max_length: int = 1000) -> str:
    """
    Validate input text length.
    Raises ValueError if text exceeds max length.
    """
    if len(text) > max_length:
        raise ValueError(
            f"Input text exceeds maximum length of {max_length} characters"
        )
    return text.strip()


def sanitize_markdown(text: str) -> str:
    """
    Sanitize markdown input to prevent XSS.
    Remove potentially dangerous content while preserving valid markdown.
    """
    # List of allowed markdown patterns
    allowed_patterns = [
        r"\*\*.+?\*\*",  # Bold
        r"\*.+?\*",  # Italic
        r"_.+?_",  # Underscore italic
        r"#{1,6}.+",  # Headers
        r"`[^`]+`",  # Inline code
        r"```[\s\S]*?```",  # Code blocks
        r"\[.+?\]\(.+?\)",  # Links
        r"- .+",  # Unordered lists
        r"\d+\. .+",  # Ordered lists
    ]

    # TODO: Implement markdown sanitization
    # For now, just strip potentially dangerous characters
    sanitized = text.replace("<", "&lt;").replace(">", "&gt;")
    return sanitized
