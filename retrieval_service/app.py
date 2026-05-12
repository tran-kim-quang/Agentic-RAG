from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from retrieval_service.client import RetrievalClient
from shared.schemas import RetrievedChunk
from typing import List

app = FastAPI(title="Retrieval Service", version="0.1.0")
client = RetrievalClient()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.get("/health")
async def health():
    try:
        collections = client.qdrant.get_collections()
        return {
            "status": "ok",
            "qdrant": "connected",
            "collections": [c.name for c in collections.collections],
        }
    except Exception as e:
        return {"status": "degraded", "qdrant": f"error: {e}"}


@app.post("/search", response_model=List[RetrievedChunk])
async def search(req: SearchRequest):
    try:
        return await client.search(req.query, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
