# Market service Dockerfile
FROM nssm-base:latest

# Copy Poetry files and install market dependencies (including OpenBB)
COPY pyproject.market.toml pyproject.toml
COPY poetry.market.lock poetry.lock
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Copy market source code and configuration
COPY market/ ./market/
COPY config/ ./config/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for market service - run scheduled price fetching (1h) and news scraping (30min)
CMD ["python", "-m", "market.scheduler", "--news-interval-minutes", "30"]
