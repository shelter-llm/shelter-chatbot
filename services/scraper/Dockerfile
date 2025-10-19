FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared modules
COPY shared/ /app/shared/

# Copy service requirements
COPY services/scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/scraper/ .

# Create data directories
RUN mkdir -p /app/data/raw /app/data/processed

# Expose port
EXPOSE 8002

# Run the service
CMD ["python", "main.py"]
