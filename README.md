# Agentic RAG — AI Sales Assistant (Bất động sản)

Hệ thống Agentic RAG đa phương thức cho trợ lý AI sales bất động sản.

## Kiến trúc

```
User / Avatar UI
    → Orchestrator Service (FastAPI + LangGraph)  :8021
    → Retrieval Service (Qdrant + Embedding)        :8011
    → Ingest Service (Parse + Chunk + Embed)
    → Ollama (Local GPU or Cloud API)              :11434 / remote
```

## Quick start

### 1. Cấu hình môi trường

```bash
cp .env.example .env
# Sửa .env — nếu dùng Ollama Cloud, điền OLLAMA_LLM_HOST và OLLAMA_API_KEY
```

### 2. Khởi động infrastructure

```bash
make infra      # Qdrant + Redis (+ Ollama local nếu cần)
```

### 3. Cài dependencies

```bash
make install
```

### 4. Chạy services

Local dev (hot reload):
```bash
make dev
```

Hoặc Docker:
```bash
make up
```

### 5. Ingest + smoke test

```bash
make smoke
```

## Ollama Cloud / Remote

Để dùng Ollama Cloud hoặc remote server:

```bash
export OLLAMA_LLM_HOST=https://api.ollama.com
export OLLAMA_API_KEY=sk-xxxxxxxx
```

Hệ thống tự động gửi `Authorization: Bearer <token>` khi `OLLAMA_API_KEY` được đặt.

## API

- `POST /chat` — Chat agent (JSON)
- `POST /chat/stream` — Streaming
- `POST /search` — Retrieval
- `GET /health` — Health check

## Client

- CLI: `make client`
- Web: Mở `client/index.html`

## Test

```bash
make test
make benchmark
```

## Stack

FastAPI, LangGraph, Qdrant, Redis, Ollama (local/cloud)
