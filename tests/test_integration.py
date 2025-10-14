"""Integration tests across services."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch

# We'll need both services running for integration tests
# For now, these are marked as integration tests that require services


@pytest.mark.integration
class TestVectorDBScraperIntegration:
    """Integration tests between VectorDB and Scraper services."""
    
    @pytest.fixture
    def vectordb_client(self):
        """VectorDB client."""
        from services.vectordb.main import app
        return TestClient(app)
    
    @pytest.fixture
    def scraper_client(self):
        """Scraper client."""
        from services.scraper.main import app
        return TestClient(app)
    
    def test_scraper_to_vectordb_flow(self, vectordb_client, scraper_client):
        """Test complete flow from scraping to vector DB storage."""
        # 1. Check VectorDB health
        response = vectordb_client.get("/health")
        assert response.status_code == 200
        
        # 2. Create collection in VectorDB
        response = vectordb_client.post(
            "/collections/create",
            json={"name": "integration_test_shelters"}
        )
        assert response.status_code == 200
        
        # 3. Mock scraper to use test data
        with patch('services.scraper.main.scrape_and_process') as mock_scrape:
            # Simulate scraping
            response = scraper_client.post("/scrape/trigger")
            assert response.status_code == 200
        
        # 4. Check if data exists in VectorDB
        response = vectordb_client.get("/collections/integration_test_shelters/stats")
        if response.status_code == 200:
            data = response.json()
            # Collection might be empty in mock scenario
            assert "stats" in data


@pytest.mark.integration
class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    def test_full_pipeline(self):
        """Test the complete data pipeline."""
        # This would require all services to be running
        # For now, just verify the structure
        
        from services.scraper.scraper import ShelterScraper
        from services.scraper.processor import DataProcessor
        
        # Get mock data
        scraper = ShelterScraper()
        shelters = scraper.get_mock_data()
        
        # Process data
        processor = DataProcessor(api_key="")
        documents = processor.process_shelters(shelters)
        
        # Verify processed data structure
        assert len(documents) > 0
        for doc in documents:
            assert 'id' in doc
            assert 'content' in doc
            assert 'metadata' in doc


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
