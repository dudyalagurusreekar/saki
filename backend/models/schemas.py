from pydantic import BaseModel, Field
from typing import Optional, List


# -------------------------
# CHAT REQUEST
# -------------------------
class ChatRequest(BaseModel):
    """
    Input from frontend → backend
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User input message"
    )


# -------------------------
# CHAT RESPONSE (optional but recommended)
# -------------------------
class ChatResponse(BaseModel):
    """
    Output from backend → frontend
    """

    response: str
    intent: Optional[str] = None


# -------------------------
# MEMORY RESPONSE
# -------------------------
class MemoryItem(BaseModel):
    user: str
    saki: str


class MemoryResponse(BaseModel):
    conversation_history: List[MemoryItem]


# -------------------------
# SYSTEM / HEALTH RESPONSE
# -------------------------
class HealthResponse(BaseModel):
    status: str


class ConfigResponse(BaseModel):
    privacy_mode: str
    model_fast: str
    model_emo: str
    max_memory: int