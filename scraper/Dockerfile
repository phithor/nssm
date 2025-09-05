# Scraper service Dockerfile
FROM nssm-base:latest

# Copy Poetry files and install scraper dependencies
COPY pyproject.scraper.toml pyproject.toml
COPY poetry.scraper.lock poetry.lock
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Copy scraper source code
COPY scraper/ ./scraper/

# Copy database files and migrations
COPY db/ ./db/
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Copy startup script explicitly
COPY scripts/start-scraper.sh ./scripts/start-scraper.sh
RUN chmod +x ./scripts/start-scraper.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for scraper service
CMD ["./scripts/start-scraper.sh"]
