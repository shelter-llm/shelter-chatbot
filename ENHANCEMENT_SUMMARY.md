# Shelter Chatbot Enhancement Summary

## Architecture Overview

The **Uppsala Shelter Chatbot** is a microservice-based RAG (Retrieval Augmented Generation) application with the following components:

### Services Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Network                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   VectorDB   │    │   Scraper    │    │  LLM Engine  │  │
│  │  (Port 8000) │◄───┤ (Port 8002)  │    │ (Port 8001)  │  │
│  │              │    │              │    │              │  │
│  │  ChromaDB    │    │ Web Scraper  │    │ RAG + Gemini │  │
│  │              │    │ + Processor  │    │              │  │
│  └──────┬───────┘    └──────────────┘    └──────┬───────┘  │
│         │                                         │          │
│         └─────────────────┬─────────────────────┘          │
│                           │                                  │
│                    ┌──────▼───────┐                         │
│                    │      UI       │                         │
│                    │  (Port 7860)  │                         │
│                    │               │                         │
│                    │    Gradio     │                         │
│                    │  + Folium Map │                         │
│                    └───────────────┘                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Service Details

#### 1. **VectorDB Service** (`services/vectordb/`)
- **Technology**: ChromaDB with persistent storage
- **Port**: 8000
- **Purpose**: Vector database for semantic search
- **Endpoints**:
  - `/health` - Health check
  - `/collections/*` - Collection management
  - `/documents/*` - Document CRUD operations
  - `/query` - Semantic search queries
- **Storage**: `./chromadb_data` (persisted volume)

#### 2. **Scraper Service** (`services/scraper/`)
- **Technology**: Python + BeautifulSoup + APScheduler
- **Port**: 8002
- **Purpose**: Scrapes Uppsala shelter data from allaskyddsrum.se
- **Endpoints**:
  - `/health` - Health check
  - `/scrape/status` - Get scrape status
  - `/scrape/trigger` - Manually trigger scrape
- **Features**:
  - Scheduled scraping (cron: `0 2 * * *` = daily at 2 AM)
  - Data processing and chunking
  - Embedding generation via Gemini
  - **NEW**: Smart startup check to avoid redundant scraping

#### 3. **LLM Engine Service** (`services/llm-engine/`)
- **Technology**: FastAPI + Gemini 2.0 Flash + LangChain
- **Port**: 8001
- **Purpose**: RAG (Retrieval Augmented Generation) engine
- **Endpoints**:
  - `/health` - Health check
  - `/chat` - Standard chat endpoint
  - `/chat/stream` - Streaming chat with SSE
  - `/query` - Direct vector search
- **Features**:
  - Context-aware responses using RAG
  - Streaming responses for better UX
  - Multi-language support (Swedish/English)
  - Location-aware shelter recommendations

#### 4. **UI Service** (`services/ui/`)
- **Technology**: Gradio + Folium
- **Port**: 7860
- **Purpose**: User interface with chat and map
- **Features**:
  - Bilingual interface (Swedish/English)
  - Real-time streaming chat responses
  - Interactive Folium map with shelter markers
  - Click-to-select location on map
  - Source citations for transparency
  - Mobile-friendly responsive design

## Enhancement: Smart Scraper Initialization

### Problem
Previously, the scraper would **always run a full scrape on every `docker compose up`**, even if the data already existed in the database. This caused:
- Unnecessary API calls
- Longer startup times
- Wasted resources
- Potential rate limiting issues

### Solution
Added a `check_data_exists()` function that:
1. Queries the VectorDB on startup
2. Checks if the `uppsala_shelters` collection exists
3. Checks if it contains documents
4. **Only scrapes if no data exists**

### Implementation

#### New Function: `check_data_exists()`
```python
async def check_data_exists() -> bool:
    """Check if shelter data already exists in the vector database.
    
    Returns:
        True if data exists, False otherwise
    """
    try:
        vectordb_url = config.VECTORDB_URL
        
        # Check if collection exists and has documents
        response = requests.get(
            f"{vectordb_url}/collections/{config.SHELTER_COLLECTION}/stats",
            timeout=10
        )
        
        if response.status_code == 200:
            stats = response.json().get('stats', {})
            count = stats.get('count', 0)
            logger.info(f"Vector DB collection '{config.SHELTER_COLLECTION}' has {count} documents")
            return count > 0
        else:
            logger.info(f"Collection '{config.SHELTER_COLLECTION}' does not exist yet")
            return False
            
    except Exception as e:
        logger.warning(f"Error checking if data exists: {e}")
        return False
```

#### Modified Startup Logic
```python
# Check if data already exists before running initial scrape
data_exists = await check_data_exists()

if data_exists:
    # Get the actual count of documents
    try:
        response = requests.get(
            f"{config.VECTORDB_URL}/collections/{config.SHELTER_COLLECTION}/stats",
            timeout=10
        )
        if response.status_code == 200:
            stats = response.json().get('stats', {})
            doc_count = stats.get('count', 0)
            logger.info(f"✓ Shelter data already exists in database ({doc_count} documents) - skipping initial scrape")
            scrape_status.status = "idle"
            scrape_status.shelters_scraped = doc_count
        else:
            logger.info("✓ Shelter data already exists in database - skipping initial scrape")
            scrape_status.status = "idle"
    except Exception as e:
        logger.info("✓ Shelter data already exists in database - skipping initial scrape")
        scrape_status.status = "idle"
else:
    logger.info("✗ No shelter data found in database - running initial scrape...")
    scrape_and_process()
```

### Benefits

✅ **Faster Restarts**: Services start immediately if data exists  
✅ **Resource Efficient**: No redundant API calls or web scraping  
✅ **Rate Limit Safe**: Reduces risk of hitting rate limits  
✅ **Idempotent**: Can restart services without side effects  
✅ **Transparent**: Clear logging shows what's happening  

### Behavior

#### First Startup (No Data)
```
INFO: Starting Scraper Service...
INFO: Vector DB collection 'uppsala_shelters' has 0 documents
INFO: Collection 'uppsala_shelters' does not exist yet
INFO: ✗ No shelter data found in database - running initial scrape...
INFO: Starting shelter data scraping...
INFO: Scraped 146 shelters
INFO: Processed into 146 documents
...
```

#### Subsequent Startups (Data Exists)
```
INFO: Starting Scraper Service...
INFO: Vector DB collection 'uppsala_shelters' has 146 documents
INFO: ✓ Shelter data already exists in database (146 documents) - skipping initial scrape
```

### Manual Scrape Trigger
If you need to refresh the data manually, you can still trigger a scrape:
```bash
curl -X POST http://localhost:8002/scrape/trigger
```

## Data Flow

```
1. User Query (Swedish/English)
         ↓
2. UI Service (Gradio)
         ↓
3. LLM Engine (RAG)
         ↓
4. Vector Search → ChromaDB
         ↓
5. Context Retrieval (Top 5 relevant shelters)
         ↓
6. Gemini 2.0 Flash (Generate answer)
         ↓
7. Streaming Response + Sources
         ↓
8. UI Updates (Chat + Map)
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Gemini 2.0 Flash Exp | Text generation |
| Embeddings | Gemini text-embedding-004 | Vector embeddings |
| Vector DB | ChromaDB | Semantic search |
| Web Framework | FastAPI | API services |
| UI Framework | Gradio | Chat interface |
| Maps | Folium | Interactive maps |
| Scraping | BeautifulSoup + lxml | Web scraping |
| Scheduling | APScheduler | Cron jobs |
| Orchestration | Docker Compose | Container management |

## Configuration

### Environment Variables
```bash
# API Keys
GOOGLE_API_KEY=<your-gemini-api-key>

# Scraper Config
SCRAPE_URL=https://www.allaskyddsrum.se/plats/uppsala/2666199
SCRAPE_SCHEDULE="0 2 * * *"  # Daily at 2 AM

# LLM Config
MODEL_NAME=gemini-2.0-flash-exp
TEMPERATURE=0.7

# UI Config
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
```

### Volumes
```yaml
volumes:
  - ./chromadb_data:/data  # Persistent vector storage
```

## Next Steps for Further Enhancement

1. **Add Data Refresh Endpoint**: Allow admins to force a refresh
2. **Incremental Updates**: Update only changed shelters
3. **Data Versioning**: Track different versions of scraped data
4. **Backup & Restore**: Automatic database backups
5. **Monitoring**: Add Prometheus metrics
6. **Caching**: Redis cache for frequent queries
7. **Rate Limiting**: API rate limiting on scraper
8. **Error Recovery**: Better error handling and retries
9. **Testing**: Add integration tests
10. **CI/CD**: GitHub Actions for automated testing/deployment

## Testing the Enhancement

### Start All Services
```bash
cd /home/habenhadush/github/mia/y2/p5/llm/project/shelter-chatbot
docker compose up --build
```

### Check Scraper Logs
```bash
docker logs shelter-scraper -f
```

### Expected Output (First Run)
```
✗ No shelter data found in database - running initial scrape...
Starting shelter data scraping...
```

### Expected Output (Subsequent Runs)
```
✓ Shelter data already exists in database (146 documents) - skipping initial scrape
```

### Verify Data in VectorDB
```bash
curl http://localhost:8000/collections/uppsala_shelters/stats
```

### Test Manual Scrape Trigger
```bash
curl -X POST http://localhost:8002/scrape/trigger
```

## Files Modified

- `services/scraper/main.py` - Added `check_data_exists()` function and modified startup logic

---

**Enhancement Date**: October 18, 2025  
**Status**: ✅ Implemented  
**Impact**: High (Performance & Resource Usage)
