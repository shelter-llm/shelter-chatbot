FROM python:3.12-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy service requirements
COPY services/ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/ui/ .

# Expose port
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
