from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import httpx
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
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(f"{settings.ollama_embed_host}/api/version")
            health_status["services"]["ollama_embed"] = "ok" if resp.status_code == 200 else "unreachable"
    except Exception as e:
        health_status["services"]["ollama_embed"] = f"error: {e}"

    # Check cloud LLM Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.get(f"{settings.ollama_llm_host}/api/version", headers=settings.ollama_headers())
            health_status["services"]["ollama_llm"] = "ok" if resp.status_code == 200 else "unreachable"
    except Exception as e:
        health_status["services"]["ollama_llm"] = f"error: {e}"

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
