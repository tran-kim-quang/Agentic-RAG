from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import httpx
import os
from shared.config import settings
from shared.schemas import UserInput, AgentResponse
from orchestrator_service.agent import run_agent
import json

app = FastAPI(title="Orchestrator Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rdb = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


async def _check_ollama(host: str, api_key: str = ""):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=5.0) as http:
        resp = await http.get(f"{host}/api/version", headers=headers)
        return resp.status_code == 200


async def _check_openai(base_url: str, api_key: str = ""):
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=5.0) as http:
        resp = await http.get(f"{base}/models", headers=headers)
        return resp.status_code == 200


@app.get("/health")
async def health():
    health_status = {"status": "ok", "services": {}}
    try:
        await rdb.ping()
        health_status["services"]["redis"] = "ok"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {e}"

    # Check local embed Ollama
    try:
        ok = await _check_ollama(settings.ollama_embed_host)
        health_status["services"]["ollama_embed"] = "ok" if ok else "unreachable"
    except Exception as e:
        health_status["services"]["ollama_embed"] = f"error: {e}"

    # Check LLM provider
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    try:
        if provider in ("ollama",):
            ok = await _check_ollama(settings.ollama_llm_host, settings.ollama_api_key)
            health_status["services"]["llm"] = "ok" if ok else "unreachable"
        elif provider in ("openai", "openai-compatible"):
            base = os.getenv("OPENAI_BASE_URL", settings.ollama_llm_host)
            key = os.getenv("OPENAI_API_KEY", settings.ollama_api_key)
            ok = await _check_openai(base, key)
            health_status["services"]["llm"] = "ok" if ok else "unreachable"
        else:
            health_status["services"]["llm"] = f"unknown provider: {provider}"
    except Exception as e:
        health_status["services"]["llm"] = f"error: {e}"

    all_ok = all(v == "ok" for v in health_status["services"].values())
    health_status["status"] = "ok" if all_ok else "degraded"
    return health_status


@app.post("/chat", response_model=AgentResponse)
async def chat(user_input: UserInput):
    try:
        profile_key = f"lead:{user_input.session_id}"
        raw = await rdb.get(profile_key)
        lead_profile = json.loads(raw) if raw else {}
        response = await run_agent(user_input, lead_profile=lead_profile)
        lead_profile["last_intent"] = response.intent
        await rdb.set(profile_key, json.dumps(lead_profile, ensure_ascii=False), ex=3600)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(user_input: UserInput):
    try:
        response = await run_agent(user_input)
        async def stream():
            for token in response.answer.split():
                yield f"{token} "
        return StreamingResponse(stream(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
