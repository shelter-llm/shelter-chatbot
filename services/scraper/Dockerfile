FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/

COPY services/scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/scraper/ .

RUN mkdir -p /app/data/raw /app/data/processed

#  service listens on port 8002
EXPOSE 8002

# Run the service
CMD ["python", "main.py"]
