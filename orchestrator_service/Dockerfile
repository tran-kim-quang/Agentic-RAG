FROM python:3.11-slim
WORKDIR /app
COPY orchestrator_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY orchestrator_service/ ./orchestrator_service/
EXPOSE 8021
CMD ["uvicorn", "orchestrator_service.app:app", "--host", "0.0.0.0", "--port", "8021"]
