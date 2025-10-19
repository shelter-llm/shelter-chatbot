"""FastAPI application for Vector DB service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uvicorn

from chromadb_manager import ChromaDBManager
from shared.models import HealthResponse
from shared.config import VectorDBConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Shelter Vector DB Service",
    description="Vector database service for Uppsala shelter chatbot",
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

# Initialize ChromaDB manager
config = VectorDBConfig()
db_manager = ChromaDBManager(persist_directory=config.CHROMA_PERSIST_DIRECTORY)


# Pydantic models for API
from pydantic import BaseModel

class CollectionCreate(BaseModel):
    name: str
    metadata: Optional[Dict[str, Any]] = None

class DocumentAdd(BaseModel):
    collection_name: str
    documents: List[str]
    metadatas: List[Dict[str, Any]]
    ids: List[str]
    embeddings: Optional[List[List[float]]] = None

class DocumentUpdate(BaseModel):
    collection_name: str
    ids: List[str]
    documents: Optional[List[str]] = None
    metadatas: Optional[List[Dict[str, Any]]] = None
    embeddings: Optional[List[List[float]]] = None

class DocumentDelete(BaseModel):
    collection_name: str
    ids: Optional[List[str]] = None
    where: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    collection_name: str
    query_texts: Optional[List[str]] = None
    query_embeddings: Optional[List[List[float]]] = None
    n_results: int = 5
    where: Optional[Dict[str, Any]] = None
    where_document: Optional[Dict[str, Any]] = None


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        collections = db_manager.list_collections()
        return HealthResponse(
            status="healthy",
            service="vectordb",
            timestamp=datetime.now(),
            details={
                "collections_count": len(collections),
                "collections": collections
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="vectordb",
            timestamp=datetime.now(),
            details={"error": str(e)}
        )


@app.post("/collections/create")
async def create_collection(request: CollectionCreate):
    """Create a new collection."""
    try:
        collection = db_manager.create_collection(
            name=request.name,
            metadata=request.metadata
        )
        return {
            "status": "success",
            "collection_name": request.name,
            "message": f"Collection '{request.name}' created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/list")
async def list_collections():
    """List all collections."""
    try:
        collections = db_manager.list_collections()
        return {
            "status": "success",
            "collections": collections,
            "count": len(collections)
        }
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{collection_name}/stats")
async def get_collection_stats(collection_name: str):
    """Get statistics for a collection."""
    try:
        stats = db_manager.get_collection_stats(collection_name)
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{collection_name}/documents")
async def get_all_documents(collection_name: str, limit: int = 100):
    """Get all documents from a collection (without semantic search)."""
    try:
        collection = db_manager.client.get_collection(name=collection_name)
        results = collection.get(limit=limit)
        
        # Format results as list of shelter objects
        documents = []
        for i in range(len(results.get("ids", []))):
            documents.append({
                "id": results["ids"][i] if i < len(results["ids"]) else None,
                "document": results["documents"][i] if i < len(results["documents"]) else "",
                "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
            })
        
        return {
            "status": "success",
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collections/{collection_name}/documents/by_ids")
async def get_documents_by_ids(collection_name: str, ids: List[str]):
    """Get specific documents by their IDs."""
    try:
        collection = db_manager.client.get_collection(name=collection_name)
        # Explicitly include all available fields
        results = collection.get(
            ids=ids,
            include=["documents", "metadatas", "embeddings"]
        )
        
        # Format results as list of shelter objects
        documents = []
        for i in range(len(results.get("ids", []))):
            documents.append({
                "id": results["ids"][i] if i < len(results["ids"]) else None,
                "document": results["documents"][i] if i < len(results["documents"]) else "",
                "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
            })
        
        return {
            "status": "success",
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error getting documents by IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a collection."""
    try:
        db_manager.delete_collection(collection_name)
        return {
            "status": "success",
            "message": f"Collection '{collection_name}' deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/add")
async def add_documents(request: DocumentAdd):
    """Add documents to a collection."""
    try:
        db_manager.add_documents(
            collection_name=request.collection_name,
            documents=request.documents,
            metadatas=request.metadatas,
            ids=request.ids,
            embeddings=request.embeddings
        )
        return {
            "status": "success",
            "message": f"Added {len(request.documents)} documents to '{request.collection_name}'",
            "count": len(request.documents)
        }
    except Exception as e:
        logger.error(f"Error adding documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/documents/update")
async def update_documents(request: DocumentUpdate):
    """Update documents in a collection."""
    try:
        db_manager.update_documents(
            collection_name=request.collection_name,
            ids=request.ids,
            documents=request.documents,
            metadatas=request.metadatas,
            embeddings=request.embeddings
        )
        return {
            "status": "success",
            "message": f"Updated {len(request.ids)} documents in '{request.collection_name}'",
            "count": len(request.ids)
        }
    except Exception as e:
        logger.error(f"Error updating documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/delete")
async def delete_documents(request: DocumentDelete):
    """Delete documents from a collection."""
    try:
        db_manager.delete_documents(
            collection_name=request.collection_name,
            ids=request.ids,
            where=request.where
        )
        return {
            "status": "success",
            "message": f"Documents deleted from '{request.collection_name}'"
        }
    except Exception as e:
        logger.error(f"Error deleting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_documents(request: QueryRequest):
    """Query documents in a collection."""
    try:
        results = db_manager.query(
            collection_name=request.collection_name,
            query_texts=request.query_texts,
            query_embeddings=request.query_embeddings,
            n_results=request.n_results,
            where=request.where,
            where_document=request.where_document
        )
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting Vector DB service...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
