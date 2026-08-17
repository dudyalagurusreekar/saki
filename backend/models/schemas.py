import time
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
# PRIVACY & SECURITY SCHEMAS
# -------------------------
class OutboundDataItemSchema(BaseModel):
    value_descriptor: str = Field(description="Safe descriptor of value e.g. EMAIL, PUBLIC_QUERY, API_KEY")
    classification: str = Field(description="PUBLIC, CONTEXTUAL, PERSONAL, PRIVATE, SECRET, RESTRICTED")
    source: str = "user_input"
    reason: str = "outbound_data_element"
    required_for_request: bool = True
    confidence: float = 1.0
    sensitivity: float = 0.0
    action: str = Field(default="ALLOW", description="ALLOW, SANITIZE, BLOCK, REQUIRE_CONFIRMATION")


class OutboundRequestSchema(BaseModel):
    action: str = "WEB_SEARCH"
    destination: str = "PUBLIC_SEARCH"
    method: str = "GET"
    query: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, Any] = Field(default_factory=dict)
    data_items: List[OutboundDataItemSchema] = Field(default_factory=list)
    requested_capability: str = "WEB_SEARCH"
    privacy_mode: str = "BALANCED"
    requires_confirmation: bool = False
    purpose: str = "outbound_search"


class PrivacyDecisionSchema(BaseModel):
    decision: str = Field(default="BLOCK", description="ALLOW, SANITIZE, BLOCK, REQUIRE_CONFIRMATION")
    reason: str = Field(default="Fail-closed default evaluation")
    risk_level: str = Field(default="LOW", description="LOW, MEDIUM, HIGH, CRITICAL")
    sanitized_request: str = ""
    blocked_items: List[str] = Field(default_factory=list)
    removed_items: List[str] = Field(default_factory=list)
    policy_version: str = "s2.1"
    audit_id: str = ""


# -------------------------
# ACTION DECISION SCHEMA
# -------------------------

class ActionDecisionSchema(BaseModel):
    action: str = Field(default="LOCAL_REASONING", description="LOCAL_REASONING, MEMORY_RECALL, RAG_RETRIEVAL, WEB_SEARCH, WEB_FETCH, WEB_RESEARCH, BROWSER_READ, BROWSER_INTERACT, VISION, CODING, CLARIFICATION, NO_ACTION")
    reason: str = Field(default="Standard local reasoning", description="Short summary of why action was selected")
    confidence: float = Field(default=0.90, description="Decision confidence 0.0 to 1.0")
    requires_memory: bool = False
    requires_rag: bool = False
    requires_world_access: bool = False
    requires_fresh_information: bool = False
    requires_user_confirmation: bool = False
    query_intent: str = "casual_chat"
    task_type: str = "casual_chat"
    information_need: str = "none"
    priority: str = "normal"
    fallback_action: str = "LOCAL_REASONING"
    freshness_requirement: str = "STABLE"
    context_requirements: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    planned_actions: List[str] = Field(default_factory=lambda: ["LOCAL_REASONING"])


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
# EVIDENCE SCHEMA
# -------------------------
class EvidenceItemSchema(BaseModel):
    source_type: str = Field(default="search_result", description="search_result, web_page, document, news_article")
    url: Optional[str] = None
    domain: Optional[str] = None
    title: str = "Web Evidence"
    content: str = ""
    retrieved_at: float = Field(default_factory=time.time)
    published_at: Optional[float] = None
    freshness_score: float = 1.0
    relevance_score: float = 1.0
    authority_score: float = 1.0
    confidence: float = 1.0
    provenance: Dict[str, Any] = Field(default_factory=dict)


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
    action_decision: Optional[ActionDecisionSchema] = None
    world_access_evidence: Optional[List[EvidenceItemSchema]] = None




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
