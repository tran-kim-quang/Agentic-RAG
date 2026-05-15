"""
Unified LLM client supporting Ollama and OpenAI-compatible APIs.
Usage:
    from orchestrator_service.llm_client import llm_generate
    result = await llm_generate(messages)
"""
import json
import os
import httpx
import asyncio
from typing import List, Dict, Any
from shared.config import settings


class LLMError(Exception):
    pass


# ── Provider configs ──────────────────────────────────────────────

class _OllamaProvider:
    name = "ollama"

    @staticmethod
    def build_payload(model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> dict:
        return {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": max_tokens,
            },
        }

    @staticmethod
    def parse_response(data: dict) -> str:
        msg = data.get("message", {})
        return msg.get("content", "")

    @staticmethod
    def url(base: str) -> str:
        return f"{base}/api/chat"

    @staticmethod
    def headers(api_key: str = "") -> dict:
        h = {"Content-Type": "application/json"}
        if api_key:
            h["Authorization"] = f"Bearer {api_key}"
        return h


class _OpenAIProvider:
    name = "openai"

    @staticmethod
    def build_payload(model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> dict:
        return {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

    @staticmethod
    def parse_response(data: dict) -> str:
        choices = data.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    @staticmethod
    def url(base: str) -> str:
        # Normalize base URL: strip trailing /v1 if present, then add /v1/chat/completions
        base = base.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    @staticmethod
    def headers(api_key: str = "") -> dict:
        h = {"Content-Type": "application/json"}
        if api_key:
            h["Authorization"] = f"Bearer {api_key}"
        return h


# Map provider names
_PROVIDER_MAP = {
    "ollama": _OllamaProvider,
    "openai": _OpenAIProvider,
    "openai-compatible": _OpenAIProvider,
}


def _get_provider():
    name = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    if name not in _PROVIDER_MAP:
        raise LLMError(f"Unknown LLM_PROVIDER={name}. Supported: {list(_PROVIDER_MAP.keys())}")
    return _PROVIDER_MAP[name]


def _normalize_messages(messages) -> List[Dict[str, str]]:
    """Normalize LangChain messages or plain dicts."""
    out = []
    for m in messages:
        if hasattr(m, "type") and hasattr(m, "content"):
            # LangChain message
            role = m.type
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
            out.append({"role": role, "content": str(m.content)})
        elif isinstance(m, dict):
            role = m.get("role", "user")
            out.append({"role": role, "content": str(m.get("content", ""))})
        else:
            out.append({"role": "user", "content": str(m)})
    return out


def _extract_content(raw: str) -> str:
    """Try to strip markdown code fences if the model wraps JSON in them."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Drop first line (```json or ```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Drop last line if ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


# ── Public API ──────────────────────────────────────────────────

async def llm_generate(
    messages,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
) -> str:
    """Unified generate. Accepts LangChain messages or plain dicts."""
    provider = _get_provider()
    model = model or settings.llm_model
    temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.3"))
    max_tokens = max_tokens if max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "4096"))

    norm_messages = _normalize_messages(messages)
    payload = provider.build_payload(model, norm_messages, temperature, max_tokens)

    # Determine endpoint
    if provider.name == "ollama":
        base = settings.ollama_llm_host
        api_key = settings.ollama_api_key
    else:
        base = os.getenv("OPENAI_BASE_URL", settings.ollama_llm_host)
        api_key = os.getenv("OPENAI_API_KEY", settings.ollama_api_key)

    url = provider.url(base)
    headers = provider.headers(api_key)

    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                resp = await http.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = provider.parse_response(data)
                if not content:
                    # Some providers may return empty on rate limit or tool call
                    raise LLMError(f"Empty content from provider. Response keys: {list(data.keys())}")
                return _extract_content(content)
        except (httpx.HTTPStatusError, LLMError) as e:
            last_error = e
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in {429, 502, 503, 504}:
                wait = 2 ** attempt
                await asyncio.sleep(wait)
                continue
            raise
    raise last_error


async def llm_generate_dicts(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
) -> str:
    """Same as llm_generate but accepts plain dicts directly."""
    return await llm_generate(messages, model=model, temperature=temperature, max_tokens=max_tokens)
