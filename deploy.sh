#!/bin/bash

# Uppsala Shelter Chatbot - Complete Deployment Script
# This script sets up and deploys all services

set -e  # Exit on error

echo "🏠 Uppsala Shelter Chatbot - Deployment Script"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker found"

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_success "Docker Compose found"

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from template..."
    
    cat > .env << 'EOF'
# Google Gemini API Key (Required)
GOOGLE_API_KEY=your_api_key_here

# Scraper Configuration
SCRAPE_URL=https://www.allaskyddsrum.se/skyddsrum/uppsala
SCRAPE_SCHEDULE=0 2 * * *

# LLM Configuration
MODEL_NAME=gemini-2.0-flash-exp
TEMPERATURE=0.7
MAX_TOKENS=2048

# Service URLs (for internal communication)
VECTORDB_URL=http://vectordb:8000
LLM_ENGINE_URL=http://llm-engine:8001

# UI Configuration
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
EOF
    
    print_warning "Please edit .env and add your GOOGLE_API_KEY"
    print_info "You can get a free API key from: https://makersuite.google.com/app/apikey"
    
    read -p "Press Enter when you've added your API key to .env..."
fi

# Verify API key is set (using export to avoid issues with special characters in .env)
export $(grep -v '^#' .env | grep -v '^$' | xargs)
if [ "$GOOGLE_API_KEY" = "your_api_key_here" ] || [ -z "$GOOGLE_API_KEY" ]; then
    print_error "GOOGLE_API_KEY is not set in .env file"
    exit 1
fi
print_success "GOOGLE_API_KEY is configured"

# Ask deployment mode
echo ""
print_info "Select deployment mode:"
echo "1. Full deployment (all 4 services)"
echo "2. Development mode (only vectordb + scraper)"
read -p "Enter choice [1-2]: " mode

COMPOSE_FILE="docker-compose.yml"
if [ "$mode" = "2" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    print_info "Using development mode (vectordb + scraper only)"
else
    print_info "Using full deployment (all services)"
fi

# Build services
print_info "Building Docker images..."
docker compose -f $COMPOSE_FILE build --no-cache

if [ $? -eq 0 ]; then
    print_success "Docker images built successfully"
else
    print_error "Failed to build Docker images"
    exit 1
fi

# Start services
print_info "Starting services..."
docker compose -f $COMPOSE_FILE up -d

if [ $? -eq 0 ]; then
    print_success "Services started successfully"
else
    print_error "Failed to start services"
    exit 1
fi

# Wait for services to be ready
print_info "Waiting for services to be ready..."
sleep 10

# Check service health
print_info "Checking service health..."

check_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$name is healthy"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_warning "$name is not responding (may still be starting)"
    return 1
}

check_service "Vector DB" "http://localhost:8000/health"
check_service "Scraper" "http://localhost:8002/health"

if [ "$mode" != "2" ]; then
    check_service "LLM Engine" "http://localhost:8001/health"
    # UI doesn't have a health endpoint, just check if port is open
    if nc -z localhost 7860 2>/dev/null; then
        print_success "UI is running"
    else
        print_warning "UI may still be starting"
    fi
fi

# Trigger initial scrape
print_info "Triggering initial data scrape..."
sleep 5  # Give scraper a bit more time to fully start

if curl -X POST http://localhost:8002/scrape/trigger > /dev/null 2>&1; then
    print_success "Initial scrape triggered"
    print_info "This may take 1-2 minutes to complete..."
    
    # Monitor scrape status
    for i in {1..60}; do
        STATUS=$(curl -s http://localhost:8002/scrape/status | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$STATUS" = "success" ]; then
            print_success "Data scraping completed successfully!"
            break
        elif [ "$STATUS" = "failed" ]; then
            print_error "Data scraping failed. Check logs: docker-compose logs scraper"
            break
        fi
        sleep 2
    done
else
    print_warning "Could not trigger initial scrape. You can do it manually later."
fi

# Print access information
echo ""
echo "=============================================="
print_success "Deployment Complete! 🎉"
echo "=============================================="
echo ""
echo "📍 Service URLs:"
echo ""

if [ "$mode" != "2" ]; then
    echo -e "${GREEN}🌐 Main Application (UI):${NC}"
    echo "   http://localhost:7860"
    echo ""
    echo -e "${BLUE}📚 API Documentation:${NC}"
    echo "   LLM Engine:  http://localhost:8001/docs"
fi

echo "   Vector DB:   http://localhost:8000/docs"
echo "   Scraper:     http://localhost:8002/docs"
echo ""

if [ "$mode" != "2" ]; then
    echo -e "${GREEN}💬 Try asking:${NC}"
    echo "   • Hitta skyddsrum nära Centralstationen"
    echo "   • Vilket är det största skyddsrummet?"
    echo "   • Visa skyddsrum med hiss"
    echo ""
fi

echo "📋 Useful Commands:"
echo "   View logs:     docker compose logs -f"
echo "   Stop services: docker compose down"
echo "   Restart:       docker compose restart"
echo "   Clean up:      docker compose down -v"
echo ""

echo -e "${BLUE}📖 Documentation:${NC}"
echo "   Complete Guide:  ./COMPLETE_GUIDE.md"
echo "   README:          ./README.md"
echo "   Quick Reference: ./QUICK_REFERENCE.md"
echo ""

print_info "Services will continue running in the background"
print_info "Use 'docker compose logs -f' to view real-time logs"
echo ""
