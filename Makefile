.PHONY: help install test run clean docker-up docker-down docker-logs

help:
	@echo "Shelter Chatbot - Makefile Commands"
	@echo "===================================="
	@echo "make install          - Install all dependencies with UV"
	@echo "make install-dev      - Install development dependencies"
	@echo "make test             - Run all tests"
	@echo "make test-cov         - Run tests with coverage"
	@echo "make test-unit        - Run unit tests only"
	@echo "make docker-up        - Start all services with Docker Compose"
	@echo "make docker-down      - Stop all services"
	@echo "make docker-logs      - View logs from all services"
	@echo "make run-vectordb     - Run Vector DB service locally"
	@echo "make run-scraper      - Run Scraper service locally"
	@echo "make clean            - Clean up generated files"
	@echo "make lint             - Run linting checks"

install:
	uv pip install -e ".[dev]"

install-vectordb:
	uv pip install -e ".[vectordb]"

install-scraper:
	uv pip install -e ".[scraper]"

install-test:
	uv pip install -e ".[test]"

install-dev:
	uv pip install -e ".[dev]"

test:
	pytest -v

test-cov:
	pytest --cov=services --cov=shared --cov-report=html --cov-report=term

test-unit:
	pytest -v -m "not integration"

test-integration:
	pytest -v -m "integration"

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

docker-clean:
	docker-compose down -v

run-vectordb:
	cd services/vectordb && python main.py

run-scraper:
	cd services/scraper && python main.py

scrape-now:
	curl -X POST http://localhost:8002/scrape/trigger

scrape-status:
	curl http://localhost:8002/scrape/status | jq

vectordb-health:
	curl http://localhost:8000/health | jq

vectordb-collections:
	curl http://localhost:8000/collections/list | jq

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage

lint:
	@echo "Linting would go here (ruff, mypy, etc.)"

format:
	@echo "Formatting would go here (black, isort, etc.)"

.env:
	cp .env.example .env
	@echo "Created .env file. Please add your GOOGLE_API_KEY"
