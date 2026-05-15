"""
Tavily web-search fallback for RAG.
Called when Qdrant returns fewer than 2 relevant chunks.
"""
import httpx
import os
from typing import List
from shared.schemas import RetrievedChunk


TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


async def tavily_search(query: str, max_results: int = 5) -> List[RetrievedChunk]:
    """Search the web via Tavily and return RetrievedChunk objects."""
    if not TAVILY_API_KEY:
        return []

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(TAVILY_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            chunks = []
            # Tavily can return an auto-generated answer
            answer = data.get("answer", "").strip()
            if answer:
                chunks.append(RetrievedChunk(
                    text=answer,
                    score=0.95,
                    source="tavily_answer",
                    metadata={"type": "web_summary"},
                ))

            for result in data.get("results", []):
                content = result.get("content", "").strip()
                if not content:
                    continue
                chunks.append(RetrievedChunk(
                    text=content,
                    score=0.85,
                    source=result.get("url", "tavily_web"),
                    metadata={
                        "title": result.get("title", ""),
                        "type": "web",
                    },
                ))
            return chunks
    except Exception as e:
        print(f"[WARN] Tavily search failed: {e}")
        return []
