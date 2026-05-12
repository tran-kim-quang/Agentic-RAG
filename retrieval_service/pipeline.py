"""Query rewrite and retrieval pipeline."""
import httpx
from shared.config import settings


async def rewrite_query(original: str) -> str:
    """Rewrite user query into a concise search-friendly form."""
    prompt = (
        "Rewrite the following real-estate customer question into a concise search query. "
        "Keep only key terms (project name, room type, budget, policy).\n\n"
        f"Question: {original}\nSearch query:"
    )
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            f"{settings.ollama_llm_host}/api/generate",
            headers=settings.ollama_headers(),
            json={
                "model": settings.llm_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 64},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
