FROM python:3.11-slim
WORKDIR /app
COPY ingest_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY retrieval_service/ ./retrieval_service/
COPY ingest_service/ ./ingest_service/
CMD ["python", "-m", "ingest_service.pipeline"]
