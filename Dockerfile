# Dashboard service Dockerfile
FROM nssm-base:latest

# Expose Streamlit port
EXPOSE 8501

# Health check for Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501').raise_for_status()" || exit 1

# Default command for dashboard service
CMD ["poetry", "run", "streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
