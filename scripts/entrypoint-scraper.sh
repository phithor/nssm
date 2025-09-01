#!/bin/bash

# NSSM Scraper Service Entrypoint
# Handles scraping operations with scheduling

echo "🕷️ Starting NSSM Scraper Service..."

# Set environment variables from .env if it exists
if [ -f /app/.env ]; then
    export $(grep -v '^#' /app/.env | xargs)
fi

# Ensure log directory exists
mkdir -p /app/logs

# Function to run scraper
run_scraper() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Running scraper..."
    cd /app && python -m scraper
}

# Default interval (can be overridden by environment variable)
SCRAPER_INTERVAL=${SCRAPER_INTERVAL_MINUTES:-60}

# Check if we're running in cron mode or manual mode
if [ "$1" = "cron" ]; then
    echo "📅 Running in cron mode - scheduling scraper every ${SCRAPER_INTERVAL} minutes"

    # Create cron job
    echo "*/${SCRAPER_INTERVAL} * * * * /app/scripts/entrypoint-scraper.sh manual" > /tmp/scraper-cron
    crontab /tmp/scraper-cron

    # Start cron daemon
    cron

    # Keep container running
    echo "⏰ Scraper scheduler started. Waiting for cron jobs..."
    tail -f /dev/null
else
    # Manual execution
    run_scraper
fi

echo "✅ Scraper service completed"
