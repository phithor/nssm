#!/bin/bash

# NSSM Unraid Storage Setup Script
# Creates the directory structure for NSSM data storage

echo "🏗️ Setting up NSSM storage directories on Unraid..."

# Base directory
BASE_DIR="/mnt/user/appdata/nssm/nssm-data"

# Create main directory structure
mkdir -p "$BASE_DIR"/{logs,data,cache,scripts}

# Create service-specific log directories
mkdir -p "$BASE_DIR"/logs/{scraper,nlp,analytics,market}

# Create data directories
mkdir -p "$BASE_DIR"/data/analytics

# Create cache directories
mkdir -p "$BASE_DIR"/cache/market

# Copy scripts to the storage location
echo "📁 Copying scripts to storage location..."
cp -r scripts/* "$BASE_DIR"/scripts/

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x "$BASE_DIR"/scripts/entrypoint-*.sh

# Set proper permissions
echo "🔐 Setting permissions..."
chown -R 1000:1000 "$BASE_DIR" 2>/dev/null || echo "Note: Could not set ownership (may need sudo)"

echo "✅ NSSM storage setup complete!"
echo ""
echo "📊 Directory structure created:"
echo "  $BASE_DIR/"
echo "  ├── logs/"
echo "  │   ├── scraper/"
echo "  │   ├── nlp/"
echo "  │   ├── analytics/"
echo "  │   └── market/"
echo "  ├── data/"
echo "  │   └── analytics/"
echo "  ├── cache/"
echo "  │   └── market/"
echo "  └── scripts/"
echo ""
echo "🚀 You can now run: docker-compose up -d"
