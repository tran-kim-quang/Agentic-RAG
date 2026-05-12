FROM python:3.11-slim
WORKDIR /app
COPY retrieval_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY retrieval_service/ ./retrieval_service/
EXPOSE 8011
CMD ["uvicorn", "retrieval_service.app:app", "--host", "0.0.0.0", "--port", "8011"]
