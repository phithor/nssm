# NLP service Dockerfile
FROM nssm-base:latest

# Copy Poetry files and install NLP dependencies (including heavy ML libraries)
COPY pyproject.nlp.toml pyproject.toml
COPY poetry.nlp.lock poetry.lock
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

# Copy NLP source code
COPY nlp/ ./nlp/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for NLP service
CMD ["python", "-m", "nlp"]
