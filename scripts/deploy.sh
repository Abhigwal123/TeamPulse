#!/bin/bash

# Deployment script for Smart Scheduling System
# Usage: ./scripts/deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.yml"

if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.yml -f docker-compose.prod.yml"
fi

echo "🚀 Deploying Smart Scheduling System ($ENVIRONMENT mode)"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if service-account-creds.json exists
if [ ! -f "service-account-creds.json" ]; then
    echo "⚠️  Warning: service-account-creds.json not found"
    echo "   Some features may not work without Google Sheets credentials"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Pull latest images
echo "📦 Pulling latest images..."
docker-compose -f $COMPOSE_FILE pull || echo "⚠️  Some images may not be available locally"

# Build images
echo "🔨 Building images..."
docker-compose -f $COMPOSE_FILE build

# Start services
echo "🚀 Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Initialize database if needed
echo "💾 Checking database..."
if ! docker-compose exec -T backend python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()" 2>/dev/null; then
    echo "⚠️  Database initialization skipped (may already exist)"
fi

# Run migrations
echo "🔄 Running database migrations..."
docker-compose exec -T backend flask db upgrade || echo "⚠️  Migrations skipped (may not be needed)"

# Check service health
echo "🏥 Checking service health..."
sleep 5

BACKEND_HEALTH=$(curl -s http://localhost:8000/api/v1/health || echo "failed")
AI_HEALTH=$(curl -s http://localhost:5001/health || echo "failed")
FRONTEND_HEALTH=$(curl -s http://localhost/health || echo "failed")

if [[ $BACKEND_HEALTH != "failed" ]]; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
fi

if [[ $AI_HEALTH != "failed" ]]; then
    echo "✅ AI Service is healthy"
else
    echo "❌ AI Service health check failed"
fi

if [[ $FRONTEND_HEALTH != "failed" ]]; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
fi

echo ""
echo "=========================================="
echo "🎉 Deployment completed!"
echo ""
echo "Services:"
echo "  Frontend:    http://localhost"
echo "  Backend API: http://localhost:8000/api/v1"
echo "  AI Service:  http://localhost:5001"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop services: docker-compose down"
echo ""

