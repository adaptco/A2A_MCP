#!/bin/bash

# Worldline Racer - Local Development Startup Script
# Usage: ./scripts/deploy-local.sh

set -e

echo "🚀 Starting Worldline Racer development environment..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

echo "✅ Docker Compose is available"
echo ""

# Clean up previous containers if they exist
echo "🧹 Cleaning up old containers..."
docker compose down 2>/dev/null || true
echo "✅ Cleanup complete"
echo ""

# Build the image
echo "🔨 Building Docker image..."
docker compose build --no-cache
echo "✅ Build complete"
echo ""

# Start services
echo "📦 Starting services..."
docker compose up -d
echo "✅ Services started"
echo ""

# Wait for application to be ready
echo "⏳ Waiting for application to start..."
for i in {1..30}; do
    if curl -s http://localhost:5000/ > /dev/null 2>&1; then
        echo "✅ Application is ready!"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 1
done

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📍 Application URL: http://localhost:5000"
echo ""
echo "📝 Useful commands:"
echo "  - View logs:        docker compose logs -f app"
echo "  - Stop services:    docker compose down"
echo "  - Rebuild:          docker compose build --no-cache"
echo ""
echo "💡 Hot-reload is enabled for client/, server/, and shared/ directories"
echo ""
