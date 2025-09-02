# Multi-stage build: Use base image as foundation
FROM python:3.11-slim-buster as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    cron \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root

# Copy source code
COPY . .

# Install the package
RUN poetry install --no-dev

# Create logs directory
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for market service
CMD ["python", "-m", "market"]
