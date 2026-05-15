from qdrant_client import QdrantClient
import sys
try:
    c = QdrantClient(host='qdrant', port=6334)
    cols = c.get_collections()
    print(f"OK gRPC 6334: {cols}")
except Exception as e:
    print(f"FAIL gRPC 6334: {e}")

try:
    c = QdrantClient(host='qdrant', port=6333, prefer_grpc=False)
    cols = c.get_collections()
    print(f"OK HTTP 6333: {cols}")
except Exception as e:
    print(f"FAIL HTTP 6333: {e}")
