#!/bin/bash

# NSSM Dashboard Cypress E2E Tests Runner
# This script starts the dashboard and runs Cypress tests

set -e

echo "🚀 Starting NSSM Dashboard Cypress Tests"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Using Docker to run tests"

    # Build and start the dashboard container
    echo "🏗️ Building dashboard container..."
    docker-compose build dashboard

    echo "🚀 Starting dashboard container..."
    docker-compose up -d dashboard

    # Wait for the dashboard to be ready
    echo "⏳ Waiting for dashboard to be ready..."
    for i in {1..30}; do
        if curl -f http://localhost:8501 > /dev/null 2>&1; then
            echo "✅ Dashboard is ready!"
            break
        fi
        echo "Waiting... ($i/30)"
        sleep 2
    done

    # Check if dashboard started successfully
    if ! curl -f http://localhost:8501 > /dev/null 2>&1; then
        echo "❌ Dashboard failed to start"
        docker-compose logs dashboard
        exit 1
    fi

    # Run Cypress tests
    echo "🧪 Running Cypress tests..."
    npx cypress run --config baseUrl=http://localhost:8501

    # Cleanup
    echo "🧹 Cleaning up containers..."
    docker-compose down

else
    echo "⚠️ Docker not available, running in development mode"

    # Check if dashboard is already running
    if curl -f http://localhost:8501 > /dev/null 2>&1; then
        echo "✅ Dashboard is already running"
    else
        echo "❌ Dashboard is not running. Please start it manually:"
        echo "   poetry run streamlit run dashboard/app.py --server.port=8501"
        exit 1
    fi

    # Run Cypress tests
    echo "🧪 Running Cypress tests..."
    npx cypress run --config baseUrl=http://localhost:8501
fi

echo "✅ Cypress tests completed successfully!"
