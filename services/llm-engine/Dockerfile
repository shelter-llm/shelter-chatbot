FROM python:3.12-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy service requirements
COPY services/llm-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/llm-engine/ .

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
