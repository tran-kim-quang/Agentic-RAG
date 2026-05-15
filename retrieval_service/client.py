import httpx
import asyncio
import random
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from shared.config import settings
from shared.schemas import RetrievedChunk

random.seed(42)

class RetrievalClient:
    def __init__(self):
        try:
            self.qdrant = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                prefer_grpc=False,
            )
            self.qdrant.get_collections()
        except Exception:
            print("[WARN] Qdrant server unavailable, falling back to in-memory mode")
            self.qdrant = QdrantClient(":memory:")
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
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(
                    f"{settings.ollama_embed_host}/api/embeddings",
                    headers=settings.ollama_headers(),
                    json={"model": settings.embed_model, "prompt": text},
                )
                if resp.status_code == 200:
                    return resp.json()["embedding"]
        except Exception:
            pass
        # Fallback: deterministic pseudo-embedding for testing
        h = hash(text) % (2**31)
        rng = random.Random(h)
        vec = [rng.random() for _ in range(768)]
        # Normalize
        mag = sum(v*v for v in vec) ** 0.5
        return [v/mag for v in vec]

    async def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        vector = await self._embed(query)
        results = self.qdrant.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            RetrievedChunk(
                text=point.payload.get("text", ""),
                score=point.score,
                source=point.payload.get("source", "unknown"),
                metadata={k: v for k, v in point.payload.items() if k not in {"text"}},
            )
            for point in results.points
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
