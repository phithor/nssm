# Analytics service Dockerfile
FROM nssm-base:latest

# Install analytics-specific dependencies
COPY pyproject.analytics.toml pyproject.toml
COPY poetry.analytics.lock poetry.lock
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Copy analytics source code
COPY analytics/ ./analytics/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for analytics service
CMD ["python", "-m", "analytics"]
