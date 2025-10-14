"""Extract coordinates from map URLs and update database."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import re
import httpx
import asyncio
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VECTORDB_URL = os.getenv("VECTORDB_URL", "http://localhost:8000")


async def extract_coords_from_url(map_url: str) -> tuple:
    """Extract latitude and longitude from Google Maps URL.
    
    Args:
        map_url: Google Maps URL
        
    Returns:
        Tuple of (lat, lng) or (None, None)
    """
    if not map_url:
        return None, None
    
    # Pattern: query=LAT,LNG
    match = re.search(r'query=([0-9.]+),([0-9.]+)', map_url)
    if match:
        return float(match.group(1)), float(match.group(2))
    
    return None, None


async def get_all_documents() -> List[Dict[str, Any]]:
    """Get all documents from the database."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{VECTORDB_URL}/collections/uppsala_shelters/documents",
            params={"limit": 2000}  # Get all
        )
        response.raise_for_status()
        data = response.json()
        return data.get("documents", [])


async def update_document_metadata(doc_id: str, metadata: Dict[str, Any]):
    """Update document metadata in ChromaDB."""
    # Note: ChromaDB doesn't have a direct update endpoint for metadata
    # We need to delete and re-add the document
    # For now, we'll log what needs to be updated
    logger.info(f"Document {doc_id} needs update: lat={metadata.get('coordinates_lat')}, lng={metadata.get('coordinates_lng')}")


async def main():
    """Main function to extract and update coordinates."""
    logger.info("Fetching all documents from database...")
    documents = await get_all_documents()
    logger.info(f"Found {len(documents)} documents")
    
    needs_update = []
    has_coords = 0
    
    for doc in documents:
        metadata = doc.get("metadata", {})
        doc_id = doc.get("id")
        map_url = metadata.get("map_url")
        
        # Check if coordinates are missing
        if metadata.get("coordinates_lat") is None or metadata.get("coordinates_lng") is None:
            # Try to extract from map URL
            lat, lng = await extract_coords_from_url(map_url)
            
            if lat and lng:
                needs_update.append({
                    "id": doc_id,
                    "name": metadata.get("name"),
                    "map_url": map_url,
                    "coordinates_lat": lat,
                    "coordinates_lng": lng
                })
            else:
                logger.warning(f"Could not extract coordinates for {metadata.get('name')} (ID: {doc_id})")
        else:
            has_coords += 1
    
    logger.info(f"\nSummary:")
    logger.info(f"  Documents with coordinates: {has_coords}")
    logger.info(f"  Documents needing update: {len(needs_update)}")
    
    if needs_update:
        logger.info(f"\nFirst 5 examples of extracted coordinates:")
        for item in needs_update[:5]:
            logger.info(f"  {item['name']}: ({item['coordinates_lat']}, {item['coordinates_lng']})")
        
        logger.info(f"\n⚠️  To apply these updates, you need to re-scrape the data.")
        logger.info(f"   The scraper is already configured to extract coordinates from map URLs.")
        logger.info(f"   Run: curl -X POST http://localhost:8002/scrape/trigger")


if __name__ == "__main__":
    asyncio.run(main())
