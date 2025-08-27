#!/bin/bash

# NSSM Database Setup Script
# This script automates the database setup process

set -e  # Exit on any error

echo "🚀 Starting NSSM Database Setup..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    exit 1
fi

echo "📦 Starting database container..."
docker-compose up -d db

echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if database is responding
echo "🔍 Checking database connection..."
until docker-compose exec -T db pg_isready -U nssm_user -d nssm_db > /dev/null 2>&1; do
    echo "   Waiting for database..."
    sleep 2
done

echo "✅ Database is ready!"

echo "🐍 Installing Python dependencies..."
poetry install

echo "🗄️ Running database initialization..."
python -m db.init_db

echo "🌱 Seeding sample data..."
python -m db.seeds

echo "🧪 Running tests..."
pytest tests/test_db_models.py -v

echo "🎉 Database setup completed successfully!"
echo ""
echo "📊 Database is now ready with:"
echo "   - 4 tables (forums, posts, sentiment_agg, alerts)"
echo "   - TimescaleDB extension enabled"
echo "   - Sample data populated"
echo "   - All tests passing"
echo ""
echo "🔗 Connect to database at: localhost:5432"
echo "   Database: nssm_db"
echo "   User: nssm_user"
echo "   Password: nssm_password"
echo ""
echo "📚 For more information, see db/README.md"
