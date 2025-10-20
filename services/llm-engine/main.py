"""FastAPI application for LLM Engine service with LangChain RAG."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import uvicorn
import httpx
from datetime import datetime
import json

from rag_engine import RAGEngine
from shared.config import LLMEngineConfig
from geocoding import get_geocoding_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Engine Service",
    description="LLM Engine with RAG for Uppsala shelter chatbot",
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

# Initialize configuration and RAG engine
config = LLMEngineConfig()
rag_engine = RAGEngine(
    api_key=config.GOOGLE_API_KEY,
    vectordb_url=config.VECTORDB_URL,
    model_name=config.MODEL_NAME,
    temperature=config.TEMPERATURE,
    max_tokens=config.MAX_TOKENS
)


# Request/Response models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role of the message sender (user/assistant/system)")
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of the message")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User's message/question")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=[],
        description="Previous conversation history for context"
    )
    language: Optional[str] = Field(
        default="sv",
        description="Language for the response (sv/en)"
    )
    max_context_docs: Optional[int] = Field(
        default=5,
        description="Maximum number of context documents to retrieve"
    )
    user_location: Optional[Dict[str, float]] = Field(
        default=None,
        description="User's location with latitude and longitude"
    )


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Assistant's response")
    sources: List[Dict[str, Any]] = Field(
        default=[],
        description="Source documents used for the response"
    )
    timestamp: str = Field(..., description="Timestamp of the response")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    timestamp: str
    vectordb_status: str
    model_name: str


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting LLM Engine Service...")
    logger.info(f"Vector DB URL: {config.VECTORDB_URL}")
    logger.info(f"Model: {config.MODEL_NAME}")
    
    # test vector DB connection
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.VECTORDB_URL}/health", timeout=10.0)
            if response.status_code == 200:
                logger.info("Vector DB connection successful")
            else:
                logger.warning(f"Vector DB returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Vector DB connection failed: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    vectordb_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.VECTORDB_URL}/health", timeout=5.0)
            vectordb_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        vectordb_status = f"error: {str(e)}"
        logger.error(f"Vector DB health check failed: {e}")
    
    return HealthResponse(
        status="healthy",
        service="llm-engine",
        timestamp=datetime.utcnow().isoformat(),
        vectordb_status=vectordb_status,
        model_name=config.MODEL_NAME
    )


class GeocodeRequest(BaseModel):
    """Geocoding request model."""
    location: str = Field(..., description="Location name or address to geocode")
    bias_to_uppsala: bool = Field(default=True, description="Bias results towards Uppsala area")


class GeocodeResponse(BaseModel):
    """Geocoding response model."""
    success: bool
    lat: Optional[float] = None
    lng: Optional[float] = None
    formatted_address: Optional[str] = None
    place_name: Optional[str] = None
    query: Optional[str] = None


@app.post("/geocode", response_model=GeocodeResponse)
async def geocode_location(request: GeocodeRequest):
    """
    Geocode a location name to coordinates.
    
    Args:
        request: Geocoding request with location name
        
    Returns:
        GeocodeResponse with coordinates or error
    """
    try:
        logger.info(f"Geocoding location: '{request.location}'")
        
        geocoding_service = get_geocoding_service()
        result = await geocoding_service.geocode_location(
            request.location,
            bias_to_uppsala=request.bias_to_uppsala
        )
        
        if result:
            logger.info(f"Successfully geocoded to ({result['lat']:.4f}, {result['lng']:.4f})")
            return GeocodeResponse(
                success=True,
                lat=result["lat"],
                lng=result["lng"],
                formatted_address=result.get("formatted_address"),
                place_name=result.get("place_name"),
                query=result.get("query")
            )
        else:
            logger.warning(f"Failed to geocode location: '{request.location}'")
            return GeocodeResponse(success=False)
            
    except Exception as e:
        logger.error(f"Error geocoding location: {e}", exc_info=True)
        return GeocodeResponse(success=False)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process chat request with RAG.
    
    Args:
        request: Chat request containing message and context
        
    Returns:
        ChatResponse with assistant's answer and sources
    """
    try:
        logger.info(f"Processing chat request: '{request.message}' (language: {request.language})")
        
        # Generate response using RAG
        response, sources = await rag_engine.generate_response(
            query=request.message,
            conversation_history=request.conversation_history,
            language=request.language,
            max_context_docs=request.max_context_docs
        )
        
        logger.info(f"Generated response with {len(sources)} sources")
        
        return ChatResponse(
            response=response,
            sources=sources,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Process chat request with streaming RAG.
    
    Args:
        request: Chat request containing message and context
        
    Returns:
        StreamingResponse with Server-Sent Events
    """
    async def event_generator():
        """Generate SSE events for streaming response."""
        try:
            logger.info(f"Processing streaming chat request: '{request.message}' (language: {request.language})")
            
            # Stream response using RAG
            async for chunk in rag_engine.generate_response_stream(
                query=request.message,
                conversation_history=request.conversation_history,
                language=request.language or "sv",
                max_context_docs=request.max_context_docs or 5,
                user_location=request.user_location
            ):
                # Send chunk 
                yield f"data: {json.dumps(chunk)}\n\n"
            
            # Send done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" 
        }
    )


@app.post("/query")
async def query_shelters(query: str, language: str = "sv", max_results: int = 5):
    """
    Query shelters without full RAG pipeline (for testing).
    
    Args:
        query: Search query
        language: Response language
        max_results: Maximum number of results
        
    Returns:
        Dict with results and metadata
    """
    try:
        logger.info(f"Processing simple query: '{query}'")
        
        # Retrieve relevant context
        context_docs = await rag_engine.retrieve_context(query, max_results)
        
        return {
            "query": query,
            "results": context_docs,
            "count": len(context_docs),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
