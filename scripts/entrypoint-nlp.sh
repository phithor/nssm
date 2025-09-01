#!/bin/bash

# NSSM NLP Service Entrypoint
# Handles NLP processing operations

echo "🧠 Starting NSSM NLP Service..."

# Set environment variables from .env if it exists
if [ -f /app/.env ]; then
    export $(grep -v '^#' /app/.env | xargs)
fi

# Ensure log directory exists
mkdir -p /app/logs

# Function to run NLP processing
run_nlp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Running NLP processing..."
    cd /app && python -m nlp
}

# Check if we're running in cron mode or manual mode
if [ "$1" = "cron" ]; then
    echo "📅 Running in cron mode - NLP service will process on-demand"

    # For NLP, we typically want to run on-demand rather than scheduled
    # Keep container running and wait for manual triggers
    echo "⏰ NLP service started. Ready for on-demand processing..."
    tail -f /dev/null
else
    # Manual execution
    run_nlp
fi

echo "✅ NLP service completed"
