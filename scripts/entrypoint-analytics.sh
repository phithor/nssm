#!/bin/bash

# NSSM Analytics Service Entrypoint
# Handles both manual execution and cron scheduling

echo "🚀 Starting NSSM Analytics Service..."

# Set environment variables from .env if it exists
if [ -f /app/.env ]; then
    export $(grep -v '^#' /app/.env | xargs)
fi

# Ensure log directory exists
mkdir -p /app/logs

# Function to run analytics
run_analytics() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Running analytics pipeline..."
    cd /app && python -m analytics.scheduler
}

# Check if we're running in cron mode or manual mode
if [ "$1" = "cron" ]; then
    echo "📅 Running in cron mode - scheduling hourly analytics"

    # Create cron job
    echo "0 * * * * /app/scripts/entrypoint-analytics.sh manual" > /tmp/analytics-cron
    crontab /tmp/analytics-cron

    # Start cron daemon
    cron

    # Keep container running
    echo "⏰ Analytics scheduler started. Waiting for cron jobs..."
    tail -f /dev/null
else
    # Manual execution
    run_analytics
fi

echo "✅ Analytics service completed"
