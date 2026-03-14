# Worldline Racer - Local Development Startup Script (Windows)
# Usage: .\scripts\deploy-local.ps1

Write-Host "🚀 Starting Worldline Racer development environment..." -ForegroundColor Green
Write-Host ""

# Check if Docker is running
$dockerCheck = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker and try again." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Check if docker-compose is available
try {
    $composeCheck = docker compose version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose not available"
    }
} catch {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose and try again." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker Compose is available" -ForegroundColor Green
Write-Host ""

# Clean up previous containers if they exist
Write-Host "🧹 Cleaning up old containers..." -ForegroundColor Yellow
docker compose down 2>$null
Write-Host "✅ Cleanup complete" -ForegroundColor Green
Write-Host ""

# Build the image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow
docker compose build --no-cache
Write-Host "✅ Build complete" -ForegroundColor Green
Write-Host ""

# Start services
Write-Host "📦 Starting services..." -ForegroundColor Yellow
docker compose up -d
Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# Wait for application to be ready
Write-Host "⏳ Waiting for application to start..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Application is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Application not ready yet
    }
    
    $attempt++
    Write-Host "  Attempt $attempt/$maxAttempts..."
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "🎉 Development environment is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Application URL: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Useful commands:" -ForegroundColor Yellow
Write-Host "  - View logs:        docker compose logs -f app"
Write-Host "  - Stop services:    docker compose down"
Write-Host "  - Rebuild:          docker compose build --no-cache"
Write-Host ""
Write-Host "💡 Hot-reload is enabled for client/, server/, and shared/ directories" -ForegroundColor Cyan
Write-Host ""
