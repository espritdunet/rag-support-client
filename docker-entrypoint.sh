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
    # Data directories
    DATA_DIR=/var/lib/rag-support/data \
    RAW_DIR=/var/lib/rag-support/data/raw \
    PROCESSED_DIR=/var/lib/rag-support/data/processed \
    MARKDOWN_DIR=/var/lib/rag-support/data/raw \
    CHROMA_PERSIST_DIRECTORY=/var/lib/rag-support/vector_store \
    LOG_FILE=/var/log/rag-support/app.log

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    # Create necessary directories with proper permissions
    && mkdir -p /var/lib/rag-support/data/raw \
             /var/lib/rag-support/data/processed \
             /var/lib/rag-support/vector_store \
             /var/log/rag-support \
    && chmod -R 755 /var/lib/rag-support \
    && chmod -R 755 /var/log/rag-support

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --from=builder /app /app

# Create volume mount points for persistence
VOLUME ["/var/lib/rag-support/data", "/var/lib/rag-support/vector_store", "/var/log/rag-support"]

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["all"]
