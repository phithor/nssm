#!/bin/bash

# NSSM Unraid Directory Setup Script
# Creates all required directories for Docker volumes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="/mnt/user/appdata/nssm/nssm-data"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create directory
create_directory() {
    local dir="$1"
    local description="$2"
    
    if [ ! -d "$dir" ]; then
        print_status "Creating $description: $dir"
        mkdir -p "$dir"
        chmod 755 "$dir"
        print_success "Created $description"
    else
        print_warning "$description already exists: $dir"
    fi
}

# Main function
main() {
    echo "🏗️  NSSM Unraid Directory Setup"
    echo "================================"
    
    # Create base directory
    create_directory "$BASE_DIR" "base directory"
    
    # Create log directories
    create_directory "$BASE_DIR/logs" "logs directory"
    create_directory "$BASE_DIR/logs/scraper" "scraper logs"
    create_directory "$BASE_DIR/logs/nlp" "nlp logs"
    create_directory "$BASE_DIR/logs/analytics" "analytics logs"
    create_directory "$BASE_DIR/logs/market" "market logs"
    
    # Create data directories
    create_directory "$BASE_DIR/data" "data directory"
    create_directory "$BASE_DIR/data/analytics" "analytics data"
    
    # Create cache directories
    create_directory "$BASE_DIR/cache" "cache directory"
    create_directory "$BASE_DIR/cache/market" "market cache"
    
    # Create models directory (if not already created)
    create_directory "$BASE_DIR/models" "models directory"
    
    # Create scripts directory (if not already created)
    create_directory "$BASE_DIR/scripts" "scripts directory"
    
    echo
    echo "📁 Directory Structure Created:"
    echo "================================"
    tree "$BASE_DIR" 2>/dev/null || find "$BASE_DIR" -type d | sort
    
    echo
    print_success "All directories created successfully!"
    echo
    echo "🚀 Next steps:"
    echo "   1. Run: docker-compose up -d"
    echo "   2. Check logs: docker-compose logs -f"
    echo "   3. Access dashboard: http://your-server-ip:8501"
}

# Run main function
main "$@"

