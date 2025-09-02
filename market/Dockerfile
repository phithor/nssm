# Market service Dockerfile
FROM nssm-base:latest

# Install market-specific dependencies
COPY pyproject.market.toml pyproject.toml
COPY poetry.market.lock poetry.lock
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Copy market source code
COPY market/ ./market/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for market service
CMD ["python", "-m", "market"]
