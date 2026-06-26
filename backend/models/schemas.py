from pydantic import BaseModel, Field
from typing import Any, Optional, List


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


class DurableMemoryItem(BaseModel):
    id: str
    type: str
    content: str
    importance: int
    confidence: float
    frequency: int
    score: float
    created_at: float
    last_seen: float
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserModel(BaseModel):
    learning_style: Optional[str] = None
    career_goal: Optional[str] = None
    project_focus: float = 0.0
    curiosity: float = 0.0
    technical_depth: float = 0.0
    persistence: float = 0.0
    updated_at: Optional[float] = None


class MemoryResponse(BaseModel):
    name: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    recent_mood: str = "neutral"
    conversation_history: List[MemoryItem]
    memories: List[DurableMemoryItem] = Field(default_factory=list)
    user_model: UserModel = Field(default_factory=UserModel)


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
