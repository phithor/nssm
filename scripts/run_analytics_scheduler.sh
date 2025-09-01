#!/bin/bash

# NSSM Analytics Scheduler Startup Script
# Run sentiment aggregation and anomaly detection on an hourly schedule

echo "🌟 Starting NSSM Analytics Scheduler..."
echo "This service will run analytics every hour and maintenance daily at 2 AM"
echo "Press Ctrl+C to stop the service"
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Consider activating one."
fi

# Run the scheduler
python -m analytics.scheduler

echo ""
echo "👋 Analytics scheduler stopped."
