# NLP service Dockerfile
FROM nssm-base:latest

# Expose any ports if needed (NLP service typically doesn't expose ports)
# EXPOSE <port>

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for NLP service
CMD ["python", "-m", "nlp"]
