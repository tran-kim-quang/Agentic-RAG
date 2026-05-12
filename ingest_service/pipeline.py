import sys, os, re, json
sys.path.insert(0, "/home/meocon/work/sideprj")
from retrieval_service.client import RetrievalClient
from shared.config import settings


def chunk_markdown(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0
    for sent in sentences:
        if current_len + len(sent) > chunk_size and current:
            chunks.append(" ".join(current))
            # overlap
            overlap_sents = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) <= overlap:
                    overlap_sents.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current = overlap_sents
            current_len = overlap_len
        current.append(sent)
        current_len += len(sent) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


async def ingest_documents(documents: list[dict]):
    """Ingest list of {source, text, metadata} into Qdrant."""
    client = RetrievalClient()
    all_chunks = []
    for doc in documents:
        parts = chunk_markdown(doc["text"])
        for part in parts:
            payload = {"text": part, "source": doc.get("source", "unknown")}
            payload.update(doc.get("metadata", {}))
            all_chunks.append(payload)
    await client.upsert(all_chunks)
    return len(all_chunks)
