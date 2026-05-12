# Changelog

## 0.1.0 — MVP Agentic RAG Sales Assistant

### Added
- Orchestrator Service (FastAPI + LangGraph agent) với sales workflow
- Retrieval Service (Qdrant + embedding via Ollama)
- Ingest Service (markdown chunking + upsert)
- Multimodal input gateway architecture (text-ready, extensible for voice/image)
- Intent classification: greeting, smalltalk, ask_project_info, ask_price, etc.
- Routing: fast path (<300ms) và RAG path (1-2s)
- Guardrails: hallucination check, forbidden patterns, response sanitization
- Sales workflow: discovery questions, lead profile tracking
- Session state management via Redis
- Ollama Cloud / Remote inference support with Bearer token auth
- Docker Compose cho Qdrant, Redis, Ollama (optional)
- Dockerfiles cho tất cả services
- Smoke test, benchmark retrieval, CLI client, HTML chat client
- Tests với pytest
- Makefile commands: install, dev, infra, up, test, smoke, benchmark, client
