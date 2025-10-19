"""Tests for Vector DB service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient
import tempfile
import shutil

# Import the app
from services.vectordb.main import app, db_manager
from services.vectordb.chromadb_manager import ChromaDBManager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db = ChromaDBManager(persist_directory=temp_dir)
    yield db
    shutil.rmtree(temp_dir)


class TestVectorDBHealth:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert data["service"] == "vectordb"
        assert "timestamp" in data


class TestCollectionOperations:
    """Test collection CRUD operations."""
    
    def test_create_collection(self, client):
        """Test creating a collection."""
        response = client.post(
            "/collections/create",
            json={"name": "test_collection", "metadata": {"test": "data"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["collection_name"] == "test_collection"
    
    def test_list_collections(self, client):
        """Test listing collections."""
        # Create a test collection first
        client.post(
            "/collections/create",
            json={"name": "test_list_collection"}
        )
        
        response = client.get("/collections/list")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "collections" in data
        assert isinstance(data["collections"], list)
    
    def test_get_collection_stats(self, client):
        """Test getting collection statistics."""
        collection_name = "test_stats_collection"
        
        # Create collection
        client.post(
            "/collections/create",
            json={"name": collection_name}
        )
        
        # Get stats
        response = client.get(f"/collections/{collection_name}/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stats" in data
        assert data["stats"]["name"] == collection_name
        assert data["stats"]["count"] >= 0
    
    def test_delete_collection(self, client):
        """Test deleting a collection."""
        collection_name = "test_delete_collection"
        
        # Create collection
        client.post(
            "/collections/create",
            json={"name": collection_name}
        )
        
        # Delete collection
        response = client.delete(f"/collections/{collection_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestDocumentOperations:
    """Test document CRUD operations."""
    
    @pytest.fixture(autouse=True)
    def setup_collection(self, client):
        """Setup test collection before each test."""
        self.collection_name = "test_documents_collection"
        client.post(
            "/collections/create",
            json={"name": self.collection_name}
        )
    
    def test_add_documents(self, client):
        """Test adding documents to collection."""
        response = client.post(
            "/documents/add",
            json={
                "collection_name": self.collection_name,
                "documents": ["Test document 1", "Test document 2"],
                "metadatas": [{"source": "test1"}, {"source": "test2"}],
                "ids": ["doc1", "doc2"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 2
    
    def test_query_documents(self, client):
        """Test querying documents."""
        # Add documents first
        client.post(
            "/documents/add",
            json={
                "collection_name": self.collection_name,
                "documents": ["Uppsala shelter near station", "Shelter in Gottsunda"],
                "metadatas": [{"location": "station"}, {"location": "gottsunda"}],
                "ids": ["shelter1", "shelter2"]
            }
        )
        
        # Query documents
        response = client.post(
            "/query",
            json={
                "collection_name": self.collection_name,
                "query_texts": ["station"],
                "n_results": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "results" in data
    
    def test_update_documents(self, client):
        """Test updating documents."""
        # Add document
        client.post(
            "/documents/add",
            json={
                "collection_name": self.collection_name,
                "documents": ["Original text"],
                "metadatas": [{"version": 1}],
                "ids": ["update_test"]
            }
        )
        
        # Update document
        response = client.put(
            "/documents/update",
            json={
                "collection_name": self.collection_name,
                "ids": ["update_test"],
                "documents": ["Updated text"],
                "metadatas": [{"version": 2}]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_delete_documents(self, client):
        """Test deleting documents."""
        # Add documents
        client.post(
            "/documents/add",
            json={
                "collection_name": self.collection_name,
                "documents": ["Delete me"],
                "metadatas": [{"temp": True}],
                "ids": ["delete_test"]
            }
        )
        
        # Delete document
        response = client.delete(
            "/documents/delete",
            json={
                "collection_name": self.collection_name,
                "ids": ["delete_test"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestChromaDBManager:
    """Test ChromaDB manager class."""
    
    def test_init(self, temp_db):
        """Test initialization."""
        assert temp_db.client is not None
        assert temp_db.persist_directory is not None
    
    def test_create_and_get_collection(self, temp_db):
        """Test creating and retrieving collection."""
        collection = temp_db.create_collection("test_collection")
        assert collection is not None
        assert collection.name == "test_collection"
    
    def test_add_and_query_documents(self, temp_db):
        """Test adding and querying documents."""
        # Create collection
        temp_db.create_collection("test_query")
        
        # Add documents
        temp_db.add_documents(
            collection_name="test_query",
            documents=["Test shelter 1", "Test shelter 2"],
            metadatas=[{"id": 1}, {"id": 2}],
            ids=["doc1", "doc2"]
        )
        
        # Query
        results = temp_db.query(
            collection_name="test_query",
            query_texts=["shelter"],
            n_results=2
        )
        
        assert len(results["ids"][0]) == 2
    
    def test_list_collections(self, temp_db):
        """Test listing collections."""
        temp_db.create_collection("collection1")
        temp_db.create_collection("collection2")
        
        collections = temp_db.list_collections()
        assert len(collections) >= 2
        assert "collection1" in collections
        assert "collection2" in collections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
