"""Shared data models across all services."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ShelterData(BaseModel):
    """Model for shelter information."""
    id: str
    name: str
    address: str
    capacity: Optional[int] = None
    coordinates: Optional[Dict[str, float]] = None  # {"lat": float, "lng": float}
    district: Optional[str] = None
    accessibility_features: List[str] = Field(default_factory=list)
    facilities: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    contact_info: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)


class DocumentChunk(BaseModel):
    """Model for document chunks to be embedded."""
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    shelter_id: Optional[str] = None


class QueryRequest(BaseModel):
    """Model for query requests to LLM engine."""
    query: str
    language: str = "sv"  # sv or en
    top_k: int = 5
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Model for query responses from LLM engine."""
    response: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class ScrapeStatus(BaseModel):
    """Model for scraper status."""
    status: str  # "idle", "running", "success", "error"
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    shelters_scraped: int = 0
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    """Model for health check responses."""
    status: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None
