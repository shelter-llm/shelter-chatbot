"""Data processor for chunking and embedding shelter data."""
import logging
from typing import List, Dict, Any
import hashlib
import json
import google.generativeai as genai

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processor for shelter data - chunking and embedding."""
    
    def __init__(self, api_key: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize data processor.
        
        Args:
            api_key: Google API key for embeddings
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Configure Gemini API
        if api_key:
            genai.configure(api_key=api_key)
            self.embedding_model = "models/text-embedding-004"
        else:
            logger.warning("No API key provided - embeddings will not be generated")
            self.embedding_model = None
    
    def process_shelters(self, shelters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process shelter data into chunks with metadata.
        
        Args:
            shelters: List of shelter dictionaries
            
        Returns:
            List of processed document chunks
        """
        documents = []
        
        for shelter in shelters:
            # Create main document for shelter
            main_doc = self._create_main_document(shelter)
            documents.append(main_doc)
            
            # Create additional chunks for detailed sections if needed
            if len(main_doc['content']) > self.chunk_size:
                chunks = self._chunk_text(main_doc['content'])
                for idx, chunk in enumerate(chunks[1:], 1):  # Skip first chunk (already added)
                    # Flatten metadata for chunks too
                    chunk_metadata = self._flatten_metadata(shelter)
                    chunk_metadata['chunk_index'] = idx
                    chunk_metadata['is_partial'] = True
                    
                    doc = {
                        'id': f"{shelter['id']}_chunk_{idx}",
                        'content': chunk,
                        'metadata': chunk_metadata,
                        'shelter_id': shelter['id']
                    }
                    documents.append(doc)
        
        logger.info(f"Processed {len(shelters)} shelters into {len(documents)} documents")
        return documents
    
    def _flatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten metadata for ChromaDB compatibility.
        
        ChromaDB only accepts str, int, float, or bool in metadata.
        This method flattens nested structures and converts lists to strings.
        
        Args:
            metadata: Original metadata dictionary
            
        Returns:
            Flattened metadata dictionary
        """
        flattened = {}
        
        for key, value in metadata.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                flattened[key] = value
            elif isinstance(value, dict):
                # Flatten nested dict (e.g., coordinates)
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (str, int, float, bool)):
                        flattened[f"{key}_{nested_key}"] = nested_value
            elif isinstance(value, list):
                # Convert list to comma-separated string
                if value and all(isinstance(item, str) for item in value):
                    flattened[key] = ", ".join(value)
                else:
                    flattened[key] = str(value)
            else:
                # Convert other types to string
                flattened[key] = str(value)
        
        return flattened
    
    def _create_main_document(self, shelter: Dict[str, Any]) -> Dict[str, Any]:
        """Create main document from shelter data.
        
        Args:
            shelter: Shelter dictionary
            
        Returns:
            Document dictionary
        """
        # Build comprehensive text content
        content_parts = []
        
        if shelter.get('name'):
            content_parts.append(f"Skyddsrum: {shelter['name']}")
        
        if shelter.get('address'):
            address = shelter['address']
            content_parts.append(f"Adress: {address}")
            
            # Add geographic context based on known central streets
            central_streets = ['Kungsgatan', 'Bangårdsgatan', 'Svartbäcksgatan', 'St Olofsgatan', 
                             'Drottninggatan', 'Vaksalagatan', 'S:t Persgatan', 'Dragarbrunnsgatan']
            if any(street.lower() in address.lower() for street in central_streets):
                content_parts.append("Läge: I centrala Uppsala, nära Centralstationen och centrum")
        
        if shelter.get('district'):
            district = shelter['district']
            content_parts.append(f"Stadsdel: {district}")
            
            # Add district context
            district_context = {
                'Centrum': 'Centralt läge, nära Centralstationen',
                'Flogsta': 'Väster om centrum',
                'Studentstaden': 'Väster om centrum',
                'Gottsunda': 'Söder om centrum',
                'Valsätra': 'Söder om centrum',
                'Luthagen': 'Öster om centrum',
                'Sävja': 'Öster om centrum'
            }
            if district in district_context:
                content_parts.append(f"Område: {district_context[district]}")
        
        if shelter.get('capacity'):
            content_parts.append(f"Kapacitet: {shelter['capacity']} personer")
        
        if shelter.get('description'):
            content_parts.append(f"Beskrivning: {shelter['description']}")
        
        if shelter.get('facilities'):
            facilities_text = ", ".join(shelter['facilities'])
            content_parts.append(f"Faciliteter: {facilities_text}")
        
        if shelter.get('accessibility_features'):
            accessibility_text = ", ".join(shelter['accessibility_features'])
            content_parts.append(f"Tillgänglighet: {accessibility_text}")
        
        if shelter.get('contact_info'):
            content_parts.append(f"Kontakt: {shelter['contact_info']}")
        
        if shelter.get('coordinates'):
            coords = shelter['coordinates']
            content_parts.append(f"Koordinater: Lat {coords.get('lat')}, Lng {coords.get('lng')}")
        
        if shelter.get('map_url'):
            content_parts.append(f"Google Maps: Klicka här för exakt plats och vägbeskrivning")
        
        content = "\n".join(content_parts)
        
        # Flatten metadata for ChromaDB compatibility
        flattened_metadata = self._flatten_metadata(shelter)
        
        return {
            'id': shelter['id'],
            'content': content,
            'metadata': flattened_metadata,
            'shelter_id': shelter['id']
        }
    
    def _chunk_text(self, text: str) -> List[str]:
        """Chunk text into smaller pieces with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence end
                sentence_end = text.rfind('. ', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    space = text.rfind(' ', start, end)
                    if space > start:
                        end = space
            
            chunks.append(text[start:end].strip())
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using Gemini.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.embedding_model:
            logger.warning("Embedding model not configured - returning empty embeddings")
            return [[0.0] * 768 for _ in texts]  # Return dummy embeddings
        
        try:
            embeddings = []
            
            # Process in batches to avoid rate limits
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Generate embeddings for batch
                for text in batch:
                    result = genai.embed_content(
                        model=self.embedding_model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                
                logger.info(f"Generated embeddings for batch {i // batch_size + 1}")
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        return self.generate_embeddings([text])[0]
    
    @staticmethod
    def generate_document_id(content: str, metadata: Dict[str, Any]) -> str:
        """Generate a unique ID for a document.
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            Unique document ID
        """
        # Create hash from content and key metadata
        hash_input = f"{content}_{metadata.get('name', '')}_{metadata.get('address', '')}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
