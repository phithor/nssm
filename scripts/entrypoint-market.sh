#!/bin/bash

# NSSM Market Data Service Entrypoint
# Handles market data collection operations

echo "📊 Starting NSSM Market Data Service..."

# Set environment variables from .env if it exists
if [ -f /app/.env ]; then
    export $(grep -v '^#' /app/.env | xargs)
fi

# Ensure log and cache directories exist
mkdir -p /app/logs
mkdir -p /app/cache

# Function to run market data collection
run_market() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Running market data collection..."
    cd /app && python -m market
}

# Default interval for market data (can be overridden)
MARKET_INTERVAL=${MARKET_INTERVAL_MINUTES:-30}

# Check if we're running in cron mode or manual mode
if [ "$1" = "cron" ]; then
    echo "📅 Running in cron mode - scheduling market data collection every ${MARKET_INTERVAL} minutes"

    # Create cron job
    echo "*/${MARKET_INTERVAL} * * * * /app/scripts/entrypoint-market.sh manual" > /tmp/market-cron
    crontab /tmp/market-cron

    # Start cron daemon
    cron

    # Keep container running
    echo "⏰ Market data scheduler started. Waiting for cron jobs..."
    tail -f /dev/null
else
    # Manual execution
    run_market
fi

echo "✅ Market data service completed"
