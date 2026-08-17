from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict


# -------------------------
# EMOTIONAL & COGNITIVE SCHEMAS
# -------------------------
class EmotionalStateSchema(BaseModel):
    emotion: str = "neutral"
    intensity: float = 0.3
    confidence: float = 0.7
    cause: str = "casual conversation"
    needs: List[str] = Field(default_factory=lambda: ["friendly_interaction"])


class SocialEnergySchema(BaseModel):
    energy: float = 0.75
    warmth: float = 0.85
    playfulness: float = 0.60
    seriousness: float = 0.45


class ConversationStateSchema(BaseModel):
    topic: str = "general"
    mode: str = "casual"
    task: str = "casual_chat"
    stage: str = "exploring"


class SakiAwarenessSchema(BaseModel):
    current_activity: str = "chatting"
    current_project: Optional[str] = "Saki"
    conversation_mode: str = "casual"
    emotional_state: EmotionalStateSchema = Field(default_factory=EmotionalStateSchema)
    social_energy: SocialEnergySchema = Field(default_factory=SocialEnergySchema)
    last_model: str = "phi3:latest"
    session_duration: int = 0
    recent_topic: str = "general"
    consecutive_frustrations: int = 0


class ResponsePlanSchema(BaseModel):
    goal: str = "lively_friendly_banter"
    tone: str = "playful_banter"
    depth: str = "concise"
    acknowledge_emotion: bool = False
    use_humor: bool = False
    ask_question: bool = False
    technical_detail: str = "none"


class EvaluationResultSchema(BaseModel):
    passed: bool = True
    score: float = 1.0
    persona_issues: List[str] = Field(default_factory=list)


class SakiCognitiveStateSchema(BaseModel):
    conversation: ConversationStateSchema = Field(default_factory=ConversationStateSchema)
    user_state: EmotionalStateSchema = Field(default_factory=EmotionalStateSchema)
    saki_state: SocialEnergySchema = Field(default_factory=SocialEnergySchema)
    context: Dict[str, Any] = Field(default_factory=dict)
    uncertainty: Dict[str, float] = Field(default_factory=dict)


# -------------------------
# CHAT REQUEST
# -------------------------
class ChatRequest(BaseModel):
    """
    Input from frontend -> backend
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User input message"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional active conversation ID"
    )
    attachments: Optional[List[dict]] = Field(
        default=None,
        description="Optional list of attachments"
    )


# -------------------------
# CHAT RESPONSE
# -------------------------
class ChatResponse(BaseModel):
    """
    Output from backend -> frontend
    """
    response: str
    intent: Optional[str] = None
    mode: Optional[str] = "casual"
    routing: Optional[Dict[str, Any]] = None
    awareness: Optional[SakiAwarenessSchema] = None
    plan: Optional[ResponsePlanSchema] = None
    evaluation: Optional[EvaluationResultSchema] = None


# -------------------------
# MEMORY RESPONSE
# -------------------------
class MemoryItem(BaseModel):
    user: str
    saki: str


class DurableMemoryItem(BaseModel):
    id: str
    type: str  # PREFERENCE, FACT, PROJECT, PATTERN, PROGRESS, DECISION, INSIGHT, SKILL, GOAL
    content: str
    importance: int
    confidence: float
    frequency: int
    score: float
    created_at: float
    last_seen: float
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CategorizedMemoriesSchema(BaseModel):
    preferences: List[DurableMemoryItem] = Field(default_factory=list)
    facts: List[DurableMemoryItem] = Field(default_factory=list)
    projects: List[DurableMemoryItem] = Field(default_factory=list)
    patterns: List[DurableMemoryItem] = Field(default_factory=list)
    progress: List[DurableMemoryItem] = Field(default_factory=list)
    decisions: List[DurableMemoryItem] = Field(default_factory=list)


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
    conversation_history: List[MemoryItem] = Field(default_factory=list)
    memories: List[DurableMemoryItem] = Field(default_factory=list)
    categorized: CategorizedMemoriesSchema = Field(default_factory=CategorizedMemoriesSchema)
    user_model: UserModel = Field(default_factory=UserModel)
    awareness: Optional[SakiAwarenessSchema] = None
    cognitive_state: Optional[SakiCognitiveStateSchema] = None


# -------------------------
# SYSTEM / HEALTH RESPONSE
# -------------------------
class HealthResponse(BaseModel):
    status: str


class ConfigResponse(BaseModel):
    privacy_mode: str
    model_phi3: str
    model_hermes: str
    model_qwen3: str
    model_coder: str
    model_gemma: str
    model_default: str
    max_memory: int
