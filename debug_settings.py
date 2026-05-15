import sys
sys.path.insert(0, "/app")
from shared.config import settings
print("OLLAMA_LLM_HOST:", settings.ollama_llm_host)
print("OLLAMA_EMBED_HOST:", settings.ollama_embed_host)
print("QDRANT_HOST:", settings.qdrant_host)
print("QDRANT_PORT:", settings.qdrant_port)
