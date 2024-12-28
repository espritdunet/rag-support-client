# syntax=docker/dockerfile:1

# Stage 1: Build stage
FROM python:3.11-slim-bookworm as builder

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
RUN pip install --no-cache-dir -e .

# Stage 2: Runtime stage
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Default Ollama URL (can be overridden)
    OLLAMA_BASE_URL=http://ollama:11434 \
    # Application directories
    DATA_DIR=/app/data \
    RAW_DIR=/app/data/raw \
    PROCESSED_DIR=/app/data/processed \
    CACHE_DIR=/app/data/cache \
    VECTOR_STORE_DIR=/app/data/vector_store \
    LOG_FILE=/app/logs/app.log

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    # Create necessary directories
    && mkdir -p /app/data/raw \
             /app/data/processed \
             /app/data/cache/embeddings \
             /app/data/vector_store \
             /app/data/backups \
             /app/logs \
    && chmod -R 755 /app/data \
    && chmod -R 755 /app/logs

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --from=builder /app /app

# Create volume mount points for persistence
VOLUME ["/app/data", "/app/logs"]

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["all"]
