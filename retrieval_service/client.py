import httpx
import asyncio
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from shared.config import settings
from shared.schemas import RetrievedChunk


class RetrievalClient:
    def __init__(self):
        self.qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self.collection = settings.qdrant_collection
        self._ensure_collection()

    def _ensure_collection(self):
        existing = [c.name for c in self.qdrant.get_collections().collections]
        if self.collection not in existing:
            self.qdrant.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

    async def _embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{settings.ollama_embed_host}/api/embeddings",
                headers=settings.ollama_headers(),
                json={"model": settings.embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    async def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        vector = await self._embed(query)
        results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            RetrievedChunk(
                text=hit.payload.get("text", ""),
                score=hit.score,
                source=hit.payload.get("source", "unknown"),
                metadata={k: v for k, v in hit.payload.items() if k not in {"text"}},
            )
            for hit in results
        ]

    async def upsert(self, chunks: List[dict]):
        texts = [c["text"] for c in chunks]
        embeddings = await asyncio.gather(*[self._embed(t) for t in texts])
        points = [
            PointStruct(
                id=i,
                vector=embeddings[i],
                payload=chunks[i],
            )
            for i in range(len(chunks))
        ]
        self.qdrant.upsert(collection_name=self.collection, points=points)
