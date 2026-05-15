"""
Clear Qdrant collection and ingest all markdown files from data/ folder.
Usage: cd /home/meocon/work/sideprj/Agentic-RAG && PYTHONPATH=. python3 scripts/ingest_data_folder.py
"""
import sys, os, asyncio
sys.path.insert(0, "/home/meocon/work/sideprj/Agentic-RAG")
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from shared.config import settings
from ingest_service.pipeline import chunk_markdown
from retrieval_service.client import RetrievalClient

DATA_DIR = os.getenv("DATA_DIR", "/home/meocon/work/sideprj/Agentic-RAG/data")


def load_markdown_files(directory: str):
    docs = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
                docs.append({
                    "source": f,
                    "text": text,
                    "metadata": {"type": "markdown", "path": path},
                })
    return docs


async def main():
    # 1. Connect to Qdrant
    print("[1] Connecting to Qdrant...")
    client = RetrievalClient()
    qdrant = client.qdrant
    collection = settings.qdrant_collection

    # Verify connection
    try:
        collections = qdrant.get_collections()
        print(f"    Connected. Existing collections: {[c.name for c in collections.collections]}")
    except Exception as e:
        print(f"    ERROR: Cannot connect to Qdrant: {e}")
        print(f"    Make sure Qdrant is running (make infra)")
        return

    # 2. Delete existing collection
    existing = [c.name for c in qdrant.get_collections().collections]
    if collection in existing:
        print(f"[2] Deleting existing collection '{collection}'...")
        qdrant.delete_collection(collection_name=collection)
        print(f"    Deleted.")
    else:
        print(f"[2] Collection '{collection}' does not exist yet.")

    # 3. Recreate collection
    print(f"[3] Creating collection '{collection}'...")
    qdrant.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print(f"    Created.")

    # 4. Load markdown files
    print(f"[4] Loading markdown files from {DATA_DIR}...")
    docs = load_markdown_files(DATA_DIR)
    print(f"    Found {len(docs)} markdown files:")
    for d in docs:
        print(f"      - {d['source']} ({len(d['text'])} chars)")

    # 5. Chunk documents
    print(f"[5] Chunking documents...")
    all_chunks = []
    for doc in docs:
        parts = chunk_markdown(doc["text"])
        for part in parts:
            all_chunks.append({
                "text": part,
                "source": doc["source"],
                "metadata": doc["metadata"],
            })
    print(f"    Total chunks: {len(all_chunks)}")

    # 6. Ingest into Qdrant
    print(f"[6] Upserting chunks into Qdrant...")
    await client.upsert(all_chunks)
    print(f"    Done. Ingested {len(all_chunks)} chunks into '{collection}'.")

    # 7. Verify
    print(f"[7] Verifying collection...")
    info = qdrant.get_collection(collection_name=collection)
    print(f"    Points count: {info.points_count}")

    # 8. Quick search test
    print(f"[8] Quick search test...")
    results = await client.search("căn hộ 2 phòng ngủ giá bao nhiêu", top_k=3)
    print(f"    Found {len(results)} results:")
    for i, r in enumerate(results):
        print(f"      [{i+1}] score={r.score:.3f} source={r.source}")
        print(f"          {r.text[:120]}...")


if __name__ == "__main__":
    asyncio.run(main())
