"""FastAPI application for Scraper service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
import logging
import uvicorn
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper import ShelterScraper
from processor import DataProcessor
from shared.models import ScrapeStatus, HealthResponse
from shared.config import ScraperConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Shelter Scraper Service",
    description="Data scraper service for Uppsala shelter chatbot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = ScraperConfig()
scraper = ShelterScraper()
processor = DataProcessor(
    api_key=config.GOOGLE_API_KEY,
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP
)

# Scrape status tracking
scrape_status = ScrapeStatus(
    status="idle",
    last_run=None,
    next_run=None,
    shelters_scraped=0
)

# Initialize scheduler
scheduler = BackgroundScheduler()


def scrape_and_process():
    """Main scraping and processing function."""
    global scrape_status
    
    try:
        logger.info("Starting shelter data scraping...")
        scrape_status.status = "running"
        
        # Scrape shelter data
        # Try real scraping first, fall back to mock data
        try:
            shelters = scraper.scrape_uppsala_shelters(config.SCRAPE_URL)
            if not shelters:
                logger.warning("No shelters found, using mock data")
                shelters = scraper.get_mock_data()
        except Exception as e:
            logger.error(f"Error scraping real data, using mock data: {e}")
            shelters = scraper.get_mock_data()
        
        logger.info(f"Scraped {len(shelters)} shelters")
        
        # Process shelter data
        documents = processor.process_shelters(shelters)
        logger.info(f"Processed into {len(documents)} documents")
        
        # Generate embeddings
        texts = [doc['content'] for doc in documents]
        
        try:
            embeddings = processor.generate_embeddings(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            embeddings = None
        
        # Send to Vector DB
        vectordb_url = config.VECTORDB_URL
        
        # First, ensure collection exists
        try:
            response = requests.post(
                f"{vectordb_url}/collections/create",
                json={
                    "name": config.SHELTER_COLLECTION,
                    "metadata": {"description": "Uppsala shelter data"}
                },
                timeout=30
            )
            logger.info(f"Collection creation response: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error creating collection (may already exist): {e}")
        
        # Add documents to collection
        try:
            add_request = {
                "collection_name": config.SHELTER_COLLECTION,
                "documents": texts,
                "metadatas": [doc['metadata'] for doc in documents],
                "ids": [doc['id'] for doc in documents],
            }
            
            if embeddings:
                add_request["embeddings"] = embeddings
            
            response = requests.post(
                f"{vectordb_url}/documents/add",
                json=add_request,
                timeout=60
            )
            response.raise_for_status()
            logger.info(f"Successfully added documents to vector DB: {response.json()}")
        except Exception as e:
            logger.error(f"Error adding documents to vector DB: {e}")
            raise
        
        # Update status
        scrape_status.status = "success"
        scrape_status.last_run = datetime.now()
        scrape_status.shelters_scraped = len(shelters)
        scrape_status.error_message = None
        
        logger.info("Scraping completed successfully")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        scrape_status.status = "error"
        scrape_status.last_run = datetime.now()
        scrape_status.error_message = str(e)


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="scraper",
        timestamp=datetime.now(),
        details={
            "scrape_status": scrape_status.status,
            "last_run": scrape_status.last_run.isoformat() if scrape_status.last_run else None,
            "shelters_scraped": scrape_status.shelters_scraped
        }
    )


@app.get("/scrape/status", response_model=ScrapeStatus)
async def get_scrape_status():
    """Get current scrape status."""
    # Calculate next run time
    next_run = None
    if scheduler.get_jobs():
        job = scheduler.get_jobs()[0]
        next_run = job.next_run_time
    
    return ScrapeStatus(
        status=scrape_status.status,
        last_run=scrape_status.last_run,
        next_run=next_run,
        shelters_scraped=scrape_status.shelters_scraped,
        error_message=scrape_status.error_message
    )


@app.post("/scrape/trigger")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger a scrape operation."""
    if scrape_status.status == "running":
        raise HTTPException(status_code=409, detail="Scrape already in progress")
    
    background_tasks.add_task(scrape_and_process)
    
    return {
        "status": "triggered",
        "message": "Scrape operation started in background"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler on startup."""
    global scrape_status
    
    logger.info("Starting Scraper Service...")
    
    # Schedule scraping job
    try:
        # Parse cron schedule
        cron_parts = config.SCRAPE_SCHEDULE.split()
        if len(cron_parts) == 5:
            trigger = CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4]
            )
            
            scheduler.add_job(
                scrape_and_process,
                trigger=trigger,
                id='shelter_scraper',
                name='Scrape Uppsala shelters',
                replace_existing=True
            )
            
            scheduler.start()
            
            # Get next run time
            job = scheduler.get_job('shelter_scraper')
            scrape_status.next_run = job.next_run_time
            
            logger.info(f"Scheduler started with cron: {config.SCRAPE_SCHEDULE}")
            logger.info(f"Next run: {scrape_status.next_run}")
        else:
            logger.error(f"Invalid cron schedule: {config.SCRAPE_SCHEDULE}")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
    
    # Run initial scrape
    logger.info("Running initial scrape...")
    scrape_and_process()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Scraper Service...")
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Scraper Service stopped")


if __name__ == "__main__":
    logger.info("Starting Scraper service...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
