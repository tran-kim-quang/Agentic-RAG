.PHONY: install dev test lint build infra up down smoke benchmark client

install:
	pip install -r orchestrator_service/requirements.txt
	pip install -r retrieval_service/requirements.txt
	pip install -r ingest_service/requirements.txt
	pip install pytest pytest-asyncio

dev:
	python -m uvicorn orchestrator_service.app:app --reload --port 8021 &
	python -m uvicorn retrieval_service.app:app --reload --port 8011

infra:
	docker compose -f deploy/docker-compose.yml up -d

down:
	docker compose -f deploy/docker-compose.yml down
	-docker compose -f deploy/docker-compose.internal.yml down

up:
	docker compose -f deploy/docker-compose.internal.yml up -d --build

test:
	pytest tests/ -v

lint:
	ruff check .

build:
	docker compose -f deploy/docker-compose.internal.yml build

smoke:
	python scripts/e2e_smoke_test.py

benchmark:
	python scripts/benchmark_retrieval.py

client:
	python scripts/cli_client.py
