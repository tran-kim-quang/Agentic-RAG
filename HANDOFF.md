# Agentic RAG Sales Assistant — Handoff Notes

**Project:** `/home/meocon/work/sideprj/Agentic-RAG/`
**Date:** 2026-05-15
**Session focus:** Rebuild infra, ingest data, unify LLM client, add Tavily web-search fallback

---

## 1. Infrastructure Status

| Service | Status | Port | Notes |
|---------|--------|------|-------|
| Qdrant | UP | 6334 (host) → 6333 (container) | Collection `real_estate` has 115 chunks |
| Redis | UP | 6379 | Running |
| Orchestrator | UP | 8022 (host) → 8021 (container) | Rebuilt with latest code |
| Retrieval | UP | 8012 (host) → 8011 (container) | Rebuilt with latest code |
| Local Ollama | DOWN | 11434 | Not running; embedding uses pseudo fallback |
| Ollama Cloud | UP | https://api.ollama.com | model `kimi-k2.6`, API key in `.env` |

**Start infra:** `cd /home/meocon/work/sideprj/Agentic-RAG && make infra && make up`

---

## 2. Data Ingestion

- **Source:** `/home/meocon/work/sideprj/Agentic-RAG/data/` (5 markdown files)
- **Collection:** `real_estate`
- **Chunks:** 115
- **Script:** `scripts/ingest_data_folder.py`
- **Run:** `docker run --rm --network deploy_default -v "$(pwd):/app" -w /app -e QDRANT_HOST=qdrant -e QDRANT_PORT=6333 -e DATA_DIR=/app/data python:3.11-slim bash -c 'pip install -q qdrant-client httpx "numpy<2" python-dotenv pydantic 2>/dev/null && PYTHONPATH=/app python3 scripts/ingest_data_folder.py'`

---

## 3. Key Code Changes

### 3.1 Unified LLM Client (`orchestrator_service/llm_client.py`)
- Supports `LLM_PROVIDER=ollama` and `LLM_PROVIDER=openai`
- Normalizes LangChain messages + strips markdown fences
- Retry with exponential backoff
- **Switch provider:** edit `.env` → `LLM_PROVIDER` / `LLM_MODEL` / `OPENAI_BASE_URL` / `OPENAI_API_KEY`

### 3.2 Config (`shared/config.py`)
New env vars:
- `LLM_PROVIDER=ollama`
- `LLM_TEMPERATURE=0.3`
- `LLM_MAX_TOKENS=4096`
- `OPENAI_BASE_URL=`
- `OPENAI_API_KEY=`

### 3.3 Agent Graph (`orchestrator_service/agent.py`)
Flow: `classify_intent → extract_profile → assess_plan → retrieve_context → web_search → build_answer → validate_answer → generate_followup`

Bug fixes applied:
- `retrieve_context`: `await build_rag_query(...)` with correct args
- `validate_answer`: `check_hallucination()` called synchronously with 2 args
- `generate_followup`: pass `history` and `assessment` to `generate_discovery_question_with_llm`
- `run_agent`: mutates `lead_profile` dict in-place for multi-turn accumulation

### 3.4 Web Search Fallback (`orchestrator_service/web_search.py`)
- Uses **Tavily API** (`TAVILY_API_KEY` in `.env`)
- Triggered when Qdrant `max_score < 0.65`
- Returns `RetrievedChunk` list with `source="tavily_answer"` or URLs
- Appended to RAG chunks; LLM sees both sources

**⚠️ Threshold note:** With real embedding (local Ollama), 0.65 is correct. Currently local Ollama is DOWN, so pseudo-embedding scores cluster around 0.77. If you need Tavily to trigger for out-of-DB queries while local Ollama is off, temporarily raise threshold to `0.80` in `agent.py:104`.

### 3.5 Retrieval Client (`retrieval_service/client.py`)
- Added `prefer_grpc=False` to QdrantClient constructor (HTTP only works in Docker)

### 3.6 Docker Compose (`deploy/docker-compose.internal.yml`)
- Changed host ports: orchestrator `8022:8021`, retrieval `8012:8011`
- Added `QDRANT_PORT=6333` env var for internal containers

---

## 4. Smoke Test Results

**File:** `test_output.md` (last run 2026-05-15)

Queries tested:
1. `"Xin chào, tôi đang tìm hiểu dự án Noble Palace Tây Hồ"` → ~91s
2. `"Dự án này có căn hộ 2 phòng ngủ không, giá khoảng bao nhiêu?"` → ~81s

**Known issue:** `FINAL EXTRACTED PROFILE` returns `{}` because LLM `kimi-k2.6` does not reliably return valid JSON for the extraction prompt. The RAG + follow-up pipeline still works.

**Web fallback verified:** Query `"Dự án Vinhomes Ocean Park có gì nổi bật, giá bao nhiêu?"` correctly triggers Tavily and returns web results (vnexpress.net, vinhomes.vn, etc.).

---

## 5. Testing Commands

```bash
# Health check
curl http://localhost:8022/health

# Chat API
curl -X POST http://localhost:8022/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Dự án Noble Palace có căn 2PN không?", "session_id":"test123"}'

# Retrieval standalone
curl -X POST http://localhost:8012/search \
  -H "Content-Type: application/json" \
  -d '{"query":"căn hộ 2 phòng ngủ giá rẻ","top_k":3}'

# Smoke test inside Docker
docker run --rm --network deploy_default -v "$(pwd):/app" -w /app \
  -e QDRANT_HOST=qdrant -e QDRANT_PORT=6333 \
  -e TAVILY_API_KEY="$(grep TAVILY_API_KEY .env | cut -d= -f2)" \
  deploy-orchestrator:latest bash -c \
  'pip install -q qdrant-client 2>/dev/null && PYTHONPATH=/app python3 scripts/smoke_test_docker.py'
```

---

## 6. Next Steps / TODO

1. **Start local Ollama** for real embedding (`ollama run nomic-embed-text`)
   - This fixes semantic relevance scores and allows proper Tavily thresholding.
2. **Fix JSON extraction reliability** — `extract_profile_with_llm` often fails to parse `kimi-k2.6` output. Consider:
   - Using a dedicated JSON-mode model for extraction
   - Adding regex fallback for common field patterns
   - Switching to OpenAI `gpt-4o-mini` for extraction only
3. **Speed optimization** — each query triggers 4 LLM calls (extract, assess, build_answer, followup) → ~90s per query. Options:
   - Parallelize extraction + assessment
   - Cache LLM responses for repeated questions
   - Switch to faster model for non-creative tasks
4. **Add more test queries** covering pain-point discovery, policy questions, and multi-turn conversations.
5. **Monitoring** — add tracing/logging for each LangGraph node to measure per-node latency.
