from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any


class UserInput(BaseModel):
    text: str = ""
    modality: Literal["text", "audio", "image", "video", "file"] = "text"
    session_id: str = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    text: str
    score: float
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    answer: str
    intent: str = ""
    chunks: List[RetrievedChunk] = Field(default_factory=list)
    route: Literal["fast", "rag", "multimodal", "deep"] = "fast"
    follow_up: Optional[str] = None
