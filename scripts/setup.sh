#!/bin/bash

# Initial setup script for Smart Scheduling System
# Usage: ./scripts/setup.sh

set -e

echo "🔧 Setting up Smart Scheduling System"
echo "======================================"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check for service account credentials
if [ ! -f "service-account-creds.json" ]; then
    echo "⚠️  service-account-creds.json not found"
    echo "   Please download your Google Service Account credentials and place them in the project root"
    echo "   See SETUP_GUIDE.md for instructions"
    read -p "Continue setup anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Google Service Account credentials found"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp env.example .env
    echo "✅ Created .env file. Please update it with your configuration."
    echo "   Important: Change SECRET_KEY and JWT_SECRET_KEY!"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backups
mkdir -p logs
echo "✅ Directories created"

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "======================================"
echo "✅ Setup completed!"
echo ""
echo "Next steps:"
echo "  1. Review and update .env file"
echo "  2. Run: make up (or docker-compose up -d)"
echo "  3. Initialize database: make init-db"
echo "  4. Access application at http://localhost"
echo ""

