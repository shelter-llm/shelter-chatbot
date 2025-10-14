#!/bin/bash
# Development script to run services locally

echo "🚀 Starting Shelter Chatbot Services..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and add your GOOGLE_API_KEY"
    exit 1
fi

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  UV is not installed. Please install UV first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Parse command line arguments
SERVICE=${1:-all}

case $SERVICE in
    vectordb)
        echo "🔷 Starting Vector DB service..."
        cd services/vectordb && python main.py
        ;;
    scraper)
        echo "🔷 Starting Scraper service..."
        cd services/scraper && python main.py
        ;;
    llm-engine)
        echo "🔷 Starting LLM Engine service..."
        cd services/llm-engine && python main.py
        ;;
    ui)
        echo "🔷 Starting UI service..."
        cd services/ui && python app.py
        ;;
    all)
        echo "🔷 Starting all services with Docker Compose..."
        docker-compose up
        ;;
    test)
        echo "🧪 Running tests..."
        pytest -v
        ;;
    *)
        echo "Usage: $0 {vectordb|scraper|llm-engine|ui|all|test}"
        exit 1
        ;;
esac
