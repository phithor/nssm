# NLP service Dockerfile
FROM nssm-ml-base:latest

# Copy NLP source code
COPY nlp/ ./nlp/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for NLP service
CMD ["python", "-m", "nlp"]
