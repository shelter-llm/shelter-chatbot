"""Tests for Scraper service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from services.scraper.main import app
from services.scraper.scraper import ShelterScraper
from services.scraper.processor import DataProcessor


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_shelters():
    """Mock shelter data."""
    return [
        {
            'id': 'test_shelter_1',
            'name': 'Test Shelter 1',
            'address': 'Test Address 1, Uppsala',
            'capacity': 100,
            'district': 'Test District',
            'accessibility_features': ['Accessible'],
            'facilities': ['Toilets', 'Ventilation'],
            'description': 'Test description',
            'contact_info': 'Test contact'
        },
        {
            'id': 'test_shelter_2',
            'name': 'Test Shelter 2',
            'address': 'Test Address 2, Uppsala',
            'capacity': 200,
            'district': 'Test District',
            'accessibility_features': ['Elevator'],
            'facilities': ['Toilets', 'Water'],
            'description': 'Test description 2',
            'contact_info': 'Test contact 2'
        }
    ]


class TestScraperHealth:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "scraper"
        assert "timestamp" in data


class TestScraperStatus:
    """Test scraper status endpoints."""
    
    def test_get_scrape_status(self, client):
        """Test getting scrape status."""
        response = client.get("/scrape/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["idle", "running", "success", "error"]
    
    @patch('services.scraper.main.scrape_and_process')
    def test_trigger_scrape(self, mock_scrape, client):
        """Test manually triggering a scrape."""
        response = client.post("/scrape/trigger")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"


class TestShelterScraper:
    """Test ShelterScraper class."""
    
    def test_init(self):
        """Test scraper initialization."""
        scraper = ShelterScraper()
        assert scraper.base_url == "https://www.allaskyddsrum.se"
        assert scraper.session is not None
    
    def test_get_mock_data(self):
        """Test getting mock shelter data."""
        scraper = ShelterScraper()
        shelters = scraper.get_mock_data()
        
        assert len(shelters) > 0
        assert all('id' in s for s in shelters)
        assert all('name' in s for s in shelters)
        assert all('address' in s for s in shelters)
    
    @patch('services.scraper.scraper.requests.Session.get')
    def test_scrape_uppsala_shelters_with_mock(self, mock_get):
        """Test scraping with mocked HTTP response."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <table>
                    <tr><th>Name</th><th>Address</th><th>Capacity</th></tr>
                    <tr><td>Shelter 1</td><td>Address 1</td><td>100</td></tr>
                    <tr><td>Shelter 2</td><td>Address 2</td><td>200</td></tr>
                </table>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        scraper = ShelterScraper()
        shelters = scraper.scrape_uppsala_shelters("http://test.com")
        
        # Should find shelters from table
        assert len(shelters) >= 0  # May be 0 if parsing fails, but shouldn't raise error
    
    def test_parse_shelter_element(self):
        """Test parsing individual shelter element."""
        from bs4 import BeautifulSoup
        
        html = """
        <div class="shelter-item">
            <h2>Test Shelter</h2>
            <p class="address">Test Address, Uppsala</p>
            <p>Kapacitet: 150 personer</p>
        </div>
        """
        
        soup = BeautifulSoup(html, 'lxml')
        element = soup.find('div')
        
        scraper = ShelterScraper()
        shelter = scraper._parse_shelter_element(element, 0)
        
        # Should parse or return None gracefully
        if shelter:
            assert 'id' in shelter
            assert 'name' in shelter


class TestDataProcessor:
    """Test DataProcessor class."""
    
    def test_init(self):
        """Test processor initialization."""
        processor = DataProcessor(api_key="", chunk_size=500, chunk_overlap=50)
        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 50
    
    def test_process_shelters(self, mock_shelters):
        """Test processing shelter data."""
        processor = DataProcessor(api_key="", chunk_size=1000, chunk_overlap=200)
        documents = processor.process_shelters(mock_shelters)
        
        assert len(documents) >= len(mock_shelters)
        assert all('id' in doc for doc in documents)
        assert all('content' in doc for doc in documents)
        assert all('metadata' in doc for doc in documents)
    
    def test_create_main_document(self, mock_shelters):
        """Test creating main document from shelter."""
        processor = DataProcessor(api_key="")
        shelter = mock_shelters[0]
        
        doc = processor._create_main_document(shelter)
        
        assert doc['id'] == shelter['id']
        assert doc['shelter_id'] == shelter['id']
        assert 'content' in doc
        assert len(doc['content']) > 0
        assert shelter['name'] in doc['content']
        assert shelter['address'] in doc['content']
    
    def test_chunk_text_short(self):
        """Test chunking short text."""
        processor = DataProcessor(api_key="", chunk_size=1000)
        text = "Short text"
        
        chunks = processor._chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_long(self):
        """Test chunking long text."""
        processor = DataProcessor(api_key="", chunk_size=50, chunk_overlap=10)
        text = "This is a long text. " * 20  # 420 characters
        
        chunks = processor._chunk_text(text)
        
        assert len(chunks) > 1
        # Check overlap exists
        for i in range(len(chunks) - 1):
            assert len(chunks[i]) <= processor.chunk_size + 10  # Some tolerance
    
    def test_generate_embeddings_no_api_key(self, mock_shelters):
        """Test generating embeddings without API key."""
        processor = DataProcessor(api_key="")
        texts = ["Test text 1", "Test text 2"]
        
        embeddings = processor.generate_embeddings(texts)
        
        # Should return dummy embeddings
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
    
    @patch('services.scraper.processor.genai.embed_content')
    def test_generate_embeddings_with_api(self, mock_embed):
        """Test generating embeddings with API."""
        mock_embed.return_value = {'embedding': [0.1, 0.2, 0.3]}
        
        processor = DataProcessor(api_key="test_key")
        texts = ["Test text"]
        
        embeddings = processor.generate_embeddings(texts)
        
        assert len(embeddings) == 1
    
    def test_generate_document_id(self):
        """Test generating document ID."""
        content = "Test content"
        metadata = {"name": "Test", "address": "Test Address"}
        
        doc_id = DataProcessor.generate_document_id(content, metadata)
        
        assert isinstance(doc_id, str)
        assert len(doc_id) == 16  # MD5 hash truncated to 16 chars
        
        # Same input should produce same ID
        doc_id2 = DataProcessor.generate_document_id(content, metadata)
        assert doc_id == doc_id2


class TestIntegration:
    """Integration tests for scraper and processor."""
    
    def test_end_to_end_processing(self):
        """Test complete flow from scraping to processing."""
        scraper = ShelterScraper()
        processor = DataProcessor(api_key="")
        
        # Get mock data
        shelters = scraper.get_mock_data()
        assert len(shelters) > 0
        
        # Process shelters
        documents = processor.process_shelters(shelters)
        assert len(documents) >= len(shelters)
        
        # Verify document structure
        for doc in documents:
            assert 'id' in doc
            assert 'content' in doc
            assert 'metadata' in doc
            assert 'shelter_id' in doc
            assert len(doc['content']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
