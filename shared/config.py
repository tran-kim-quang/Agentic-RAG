import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6334"))
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "real_estate")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))

    # Dual Ollama: local embed + cloud LLM
    ollama_embed_host: str = os.getenv("OLLAMA_EMBED_HOST", "http://localhost:11434")
    ollama_llm_host: str = os.getenv("OLLAMA_LLM_HOST", "http://localhost:11434")
    ollama_api_key: str = os.getenv("OLLAMA_API_KEY", "")

    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:14b")

    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    fast_response_timeout: float = float(os.getenv("FAST_RESPONSE_TIMEOUT", "0.3"))
    rag_timeout: float = float(os.getenv("RAG_TIMEOUT", "2.0"))

    def ollama_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.ollama_api_key:
            headers["Authorization"] = f"Bearer {self.ollama_api_key}"
        return headers


settings = Settings()
