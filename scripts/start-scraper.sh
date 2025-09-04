#!/bin/bash

# Start script for NSSM Scraper
# This script ensures database migrations are run before starting the scraper

set -e

echo "Starting NSSM Scraper..."

# Function to check if database is ready
check_database() {
    echo "Checking database connection..."
    python -c "
import sys
from sqlalchemy import create_engine
from config import get_database_url

try:
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
"
}

# Function to run migrations
run_migrations() {
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations completed successfully"
}

# Function to seed database
seed_database() {
    echo "Seeding database with initial data..."
    python -c "
from db.init_db import init_database
try:
    init_database()
    print('Database seeded successfully')
except Exception as e:
    print(f'Database seeding failed: {e}')
"
}

# Main execution
echo "Initializing scraper..."

# Wait for database to be ready (retry up to 30 times with 2 second intervals)
for i in {1..30}; do
    if check_database; then
        echo "Database is ready"
        break
    else
        echo "Database not ready, waiting... (attempt $i/30)"
        sleep 2
    fi
done

# Run migrations
run_migrations

# Seed database
seed_database

echo "Starting scraper service..."
exec python -m scraper run
