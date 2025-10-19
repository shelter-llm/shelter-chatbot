"""ChromaDB Manager for vector operations."""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Manager class for ChromaDB operations."""
    
    def __init__(self, persist_directory: str = "./chromadb_data"):
        """Initialize ChromaDB client.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        logger.info(f"ChromaDB initialized with persist directory: {persist_directory}")
    
    def create_collection(
        self, 
        name: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> chromadb.Collection:
        """Create or get a collection.
        
        Args:
            name: Collection name
            metadata: Optional metadata for the collection
            
        Returns:
            ChromaDB collection
        """
        try:
            collection = self.client.get_or_create_collection(
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Collection '{name}' created/retrieved successfully")
            return collection
        except Exception as e:
            logger.error(f"Error creating collection '{name}': {e}")
            raise
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None
    ) -> None:
        """Add documents to a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document texts
            metadatas: List of metadata dicts
            ids: List of document IDs
            embeddings: Optional pre-computed embeddings
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            
            if embeddings:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
            else:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            logger.info(f"Added {len(documents)} documents to collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Error adding documents to collection '{collection_name}': {e}")
            raise
    
    def query(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query a collection for similar documents.
        
        Args:
            collection_name: Name of the collection
            query_texts: List of query texts
            query_embeddings: Optional pre-computed query embeddings
            n_results: Number of results to return
            where: Optional metadata filter
            where_document: Optional document content filter
            
        Returns:
            Query results
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            
            if query_embeddings:
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=["documents", "metadatas", "distances"]  # Explicitly include all metadata
                )
            elif query_texts:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=["documents", "metadatas", "distances"]  # Explicitly include all metadata
                )
            else:
                raise ValueError("Either query_texts or query_embeddings must be provided")
            
            logger.info(f"Query executed on collection '{collection_name}'")
            return results
        except Exception as e:
            logger.error(f"Error querying collection '{collection_name}': {e}")
            raise
    
    def update_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> None:
        """Update documents in a collection.
        
        Args:
            collection_name: Name of the collection
            ids: List of document IDs to update
            documents: Optional new document texts
            metadatas: Optional new metadata
            embeddings: Optional new embeddings
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            logger.info(f"Updated {len(ids)} documents in collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Error updating documents in collection '{collection_name}': {e}")
            raise
    
    def delete_documents(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> None:
        """Delete documents from a collection.
        
        Args:
            collection_name: Name of the collection
            ids: Optional list of document IDs to delete
            where: Optional metadata filter for deletion
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            collection.delete(ids=ids, where=where)
            logger.info(f"Deleted documents from collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Error deleting documents from collection '{collection_name}': {e}")
            raise
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection statistics
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            count = collection.count()
            return {
                "name": collection_name,
                "count": count,
                "metadata": collection.metadata
            }
        except Exception as e:
            logger.error(f"Error getting stats for collection '{collection_name}': {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """List all collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise
    
    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
        """
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Error deleting collection '{collection_name}': {e}")
            raise
    
    def reset(self) -> None:
        """Reset the entire database (use with caution)."""
        try:
            self.client.reset()
            logger.warning("ChromaDB reset completed")
        except Exception as e:
            logger.error(f"Error resetting ChromaDB: {e}")
            raise
