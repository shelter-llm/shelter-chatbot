FROM python:3.12-slim

WORKDIR /app

COPY shared/ /app/shared/

COPY services/ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ui/ .

# UI service runs on port 7860 / Gradio default-localhost
EXPOSE 7860

CMD ["python", "app.py"]
