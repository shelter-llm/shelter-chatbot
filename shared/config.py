"""Shared configuration across services."""
import os
from typing import Optional


class Config:
    """Base configuration class."""
    
    # Google API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Vector DB
    VECTORDB_URL: str = os.getenv("VECTORDB_URL", "http://localhost:8000")
    VECTORDB_HOST: str = os.getenv("VECTORDB_HOST", "localhost")
    VECTORDB_PORT: int = int(os.getenv("VECTORDB_PORT", "8000"))
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chromadb_data")
    
    # Scraper
    SCRAPE_URL: str = os.getenv("SCRAPE_URL", "https://www.allaskyddsrum.se/plats/uppsala/2666199")
    SCRAPE_SCHEDULE: str = os.getenv("SCRAPE_SCHEDULE", "0 2 * * *")
    
    # LLM
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.0-flash-exp")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2048"))
    
    # Embedding
    EMBEDDING_MODEL: str = "models/text-embedding-004"  # Gemini embedding model
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Collection names
    SHELTER_COLLECTION: str = "uppsala_shelters"


class VectorDBConfig(Config):
    """Configuration for Vector DB service."""
    pass


class ScraperConfig(Config):
    """Configuration for Scraper service."""
    pass


class LLMEngineConfig(Config):
    """Configuration for LLM Engine service."""
    pass


class UIConfig(Config):
    """Configuration for UI service."""
    LLM_ENGINE_URL: str = os.getenv("LLM_ENGINE_URL", "http://localhost:8001")
    GRADIO_SERVER_NAME: str = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    GRADIO_SERVER_PORT: int = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
