# 🏠 Uppsala Shelter Chatbot

An AI-powered chatbot system for providing information about emergency shelters in Uppsala, Sweden.

## 🎯 Overview

This project implements a complete microservices-based chatbot that helps users find information about emergency shelters (skyddsrum) in Uppsala. The system uses RAG (Retrieval Augmented Generation) with Google's Gemini AI to provide accurate, context-aware responses.

### ✨ Key Features
- 🤖 **AI-Powered Chat** with Gemini 2.0 Flash
- 🗺️ **Interactive Map** with 1267+ shelter locations
- 🌍 **Multilingual** support (Swedish/English)
- 🔄 **Real-time Updates** via automated scraping
- 📱 **Responsive UI** built with Gradio
- 🎯 **RAG Pipeline** for accurate answers
- ⚡ **Fast Semantic Search** with ChromaDB

## 🏗️ Architecture

The application follows a **microservices architecture** with 4 independent services:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Scraper    │────▶│  Vector DB   │◀────│ LLM Engine  │◀────│     UI       │
│  Service    │     │  (ChromaDB)  │     │ (LangChain) │     │  (Gradio)    │
│  Port: 8002 │     │  Port: 8000  │     │ Port: 8001  │     │  Port: 7860  │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

### Services

1. **Vector Database Service** (ChromaDB) - Port 8000 ✅
   - Stores shelter embeddings (768 dimensions)
   - Provides semantic similarity search
   - Persistent storage with ChromaDB
   - Collection management API

2. **Data Scraper Service** - Port 8002 ✅
   - Scrapes 1267+ shelters from allaskyddsrum.se
   - Generates Gemini embeddings
   - Scheduled updates (daily at 2 AM)
   - Mock data fallback

3. **LLM Engine Service** - Port 8001 ✅
   - RAG implementation with LangChain
   - Gemini 2.0 Flash for responses
   - Context-aware conversations
   - Multilingual support

4. **UI Service** - Port 7860 ✅
   - Gradio chat interface
   - Interactive Folium map
   - Real-time updates
   - Swedish/English toggle

## 🚀 Quick Start

### 1. Prerequisites
```bash
- Docker & Docker Compose
- Python 3.12+
- Google Gemini API key (free tier works!)
- 4GB+ RAM
```

### 2. Setup Environment
```bash
# Clone repository
git clone <repository-url>
cd shelter-chatbot

# Create .env file
cat > .env << 'EOF'
GOOGLE_API_KEY=your_api_key_here
SCRAPE_URL=https://www.allaskyddsrum.se/skyddsrum/uppsala
MODEL_NAME=gemini-2.0-flash-exp
TEMPERATURE=0.7
EOF
```

### 3. Launch All Services
```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Initial Data Load
```bash
# Trigger first scrape
curl -X POST http://localhost:8002/scrape/trigger

# Wait ~1 minute for completion
docker-compose logs scraper
```

### 5. Access the Application
- **🌐 Main UI (Chat + Map)**: http://localhost:7860
- **📚 LLM Engine API**: http://localhost:8001/docs
- **🗄️ Vector DB API**: http://localhost:8000/docs
- **🔄 Scraper API**: http://localhost:8002/docs

## 📦 Project Structure

```
shelter-chatbot/
├── docker-compose.yml          # Docker orchestration
├── .env.example                # Environment variables template
├── pyproject.toml              # Project dependencies
├── shared/                     # Shared utilities
│   ├── models.py              # Pydantic models
│   └── config.py              # Configuration classes
├── services/
│   ├── vectordb/              # Vector DB service
│   │   ├── Dockerfile
│   │   ├── main.py           # FastAPI app
│   │   └── chromadb_manager.py
│   ├── scraper/               # Data scraper service
│   │   ├── Dockerfile
│   │   ├── main.py           # FastAPI app + scheduler
│   │   ├── scraper.py        # Web scraping logic
│   │   └── processor.py      # Data processing & embedding
│   ├── llm-engine/            # LLM engine service (TODO)
│   └── ui/                    # UI service (TODO)
├── data/
│   ├── raw/                   # Raw scraped data
│   └── processed/             # Processed data
├── tests/                     # Test suite
│   ├── test_vectordb.py
│   ├── test_scraper.py
│   └── test_integration.py
└── chromadb_data/             # Persistent vector DB storage
```

## 🧪 Development

### Install Dependencies (with UV)

```bash
# Install for specific service
uv pip install -e ".[vectordb]"
uv pip install -e ".[scraper]"
uv pip install -e ".[llm-engine]"
uv pip install -e ".[ui]"

# Install all for development
uv pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=shared --cov-report=html

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run specific service tests
pytest tests/test_vectordb.py -v
pytest tests/test_scraper.py -v
```

### Run Services Individually

**Vector DB Service:**
```bash
cd services/vectordb
python main.py
```

**Scraper Service:**
```bash
cd services/scraper
python main.py
```

### Manual Operations

**Trigger manual scrape:**
```bash
curl -X POST http://localhost:8002/scrape/trigger
```

**Check scraper status:**
```bash
curl http://localhost:8002/scrape/status
```

**Query vector DB:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "uppsala_shelters",
    "query_texts": ["shelter near station"],
    "n_results": 3
  }'
```

## 🔧 Configuration

Key environment variables in `.env`:

- `GOOGLE_API_KEY`: Google Gemini API key
- `SCRAPE_SCHEDULE`: Cron schedule for scraper (default: `0 2 * * *`)
- `SCRAPE_URL`: URL to scrape shelter data
- `MODEL_NAME`: Gemini model name (default: `gemini-2.0-flash-exp`)
- `TEMPERATURE`: LLM temperature (default: `0.7`)

## 📊 Features

### Current Implementation ✅
- Microservices architecture with Docker
- Web scraping of shelter data
- Vector storage with ChromaDB
- Embedding generation with Gemini
- Automated cron scheduling
- Comprehensive test suite
- Health check endpoints

### Coming Soon 🚧
- LLM Engine service with LangChain RAG
- Gradio UI with chat interface
- Map visualization with shelter locations
- Multilingual support (Swedish/English)
- Real-time shelter availability
- GPS-based recommendations

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.12
- **Vector DB**: ChromaDB
- **LLM**: Google Gemini Flash 2.5
- **Orchestration**: LangChain
- **UI**: Gradio
- **Scraping**: BeautifulSoup4, Requests
- **Scheduling**: APScheduler
- **Testing**: Pytest
- **Containerization**: Docker, Docker Compose

## 📝 API Documentation

Once services are running, access interactive API docs:
- Vector DB: http://localhost:8000/docs
- Scraper: http://localhost:8002/docs
- LLM Engine: http://localhost:8001/docs (coming soon)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## 📄 License

MIT License

## 👥 Authors

Uppsala Shelter Chatbot Team