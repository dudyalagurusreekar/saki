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
# EVIDENCE INTELLIGENCE SCHEMAS
# -------------------------
class SourceModelSchema(BaseModel):
    source_id: str
    domain: str
    url: str
    title: str
    source_type: str = "UNKNOWN"
    publisher: Optional[str] = None
    retrieved_at: float
    published_at: Optional[float] = None
    modified_at: Optional[float] = None
    canonical_url: str
    provider: str = "DuckDuckGo"
    is_primary: str = "UNKNOWN"
    authority: str = "UNKNOWN"


class ClaimModelSchema(BaseModel):
    claim_id: str
    text: str
    source_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    support_status: str = "SUPPORTED"
    directness: str = "DIRECT_SUPPORT"
    confidence: float = 0.90


class ConflictModelSchema(BaseModel):
    conflict_id: str
    claim_a: str
    claim_b: str
    category: str = "NO_CONFLICT"
    resolution_hint: Optional[str] = None


class EvidencePackageSchema(BaseModel):
    query: str
    retrieved_at: float
    sources: List[SourceModelSchema] = Field(default_factory=list)
    claims: List[ClaimModelSchema] = Field(default_factory=list)
    evidence_items: List[EvidenceItemSchema] = Field(default_factory=list)
    conflicts: List[ConflictModelSchema] = Field(default_factory=list)
    source_diversity: Dict[str, Any] = Field(default_factory=dict)
    freshness_summary: str = "CURRENT"
    quality_summary: str = "HIGH"
    evidence_status: str = "SUFFICIENT"
    evidence_policy_version: str = "s4.1"


# -------------------------
# RESEARCH SCHEMAS
# -------------------------
class ResearchStepSchema(BaseModel):
    step_id: str
    query: str
    purpose: str
    status: str = "PLANNED"  # PLANNED, RUNNING, COMPLETED, FAILED, SKIPPED
    result_count: int = 0
    evidence_count: int = 0
    timestamp: float = Field(default_factory=time.time)


class ResearchBudgetSchema(BaseModel):
    max_searches: int = 3
    max_fetches: int = 2
    max_depth: int = 3
    max_runtime: float = 15.0
    max_total_results: int = 15
    max_total_bytes: int = 1000000


class ResearchPlanSchema(BaseModel):
    research_id: str
    original_question: str
    objective: str
    initial_queries: List[str] = Field(default_factory=list)
    budget: ResearchBudgetSchema = Field(default_factory=ResearchBudgetSchema)
    stop_conditions: List[str] = Field(default_factory=list)


class ResearchStateSchema(BaseModel):
    completed_steps: List[ResearchStepSchema] = Field(default_factory=list)
    pending_steps: List[ResearchStepSchema] = Field(default_factory=list)
    budget_used: Dict[str, Any] = Field(default_factory=dict)
    stop_reason: Optional[str] = None


class ResearchResultSchema(BaseModel):
    research_id: str
    question: str
    summary: str
    evidence_package: Optional[EvidencePackageSchema] = None
    sources_consulted: int = 0
    searches_performed: int = 0
    conflicts_detected: int = 0
    limitations: List[str] = Field(default_factory=list)
    stop_reason: str = "EVIDENCE_SUFFICIENT"
    research_duration: float = 0.0


# -------------------------
# MEMORY ADMISSION SCHEMAS
# -------------------------
class MemoryCandidateSchema(BaseModel):
    candidate_id: str
    content: str
    memory_type: str = "WEB_EVIDENCE"
    source_type: str = "WEB"
    source_id: Optional[str] = None
    confidence: float = 0.90
    importance: str = "NORMAL"
    privacy_classification: str = "PUBLIC"
    created_at: float = Field(default_factory=time.time)


class MemoryAdmissionDecisionSchema(BaseModel):
    decision: str = "REJECT"  # ADMIT, REJECT, DEFER, REQUIRE_CONFIRMATION
    reason: str
    memory_type: str = "WEB_EVIDENCE"
    confidence: float = 0.90
    importance: str = "NORMAL"
    expiration: str = "EPHEMERAL"
    conflict_status: str = "NO_CONFLICT"


class MemoryConflictSchema(BaseModel):
    memory_id: str
    old_value: str
    new_value: str
    conflict_type: str = "DIRECT_CONFLICT"
    resolution_status: str = "UNRESOLVED"


class MemoryRecordSchema(BaseModel):
    memory_id: str
    content: str
    type: str = "PERSONAL_MEMORY"
    source: str = "USER"
    confidence: float = 0.95
    importance: str = "NORMAL"
    privacy_level: str = "PRIVATE"
    created_at: float = Field(default_factory=time.time)
    status: str = "ACTIVE"
    knowledge_status: str = "VERIFIED"


# -------------------------
# BROWSER CONTROLLER SCHEMAS
# -------------------------
class BrowserActionSchema(BaseModel):
    action_type: str = "BROWSER_READ"  # BROWSER_READ, BROWSER_INTERACT
    url: str
    target_element: Optional[str] = None
    input_text: Optional[str] = None
    user_confirmed: bool = False


class BrowserPermissionSchema(BaseModel):
    mode: str = "READ_ONLY"  # READ_ONLY, INTERACTIVE, BLOCKED
    allowed_actions: List[str] = Field(default_factory=lambda: ["NAVIGATE", "READ_DOM", "EXTRACT_TEXT"])
    user_confirmed: bool = False


class BrowserObservationSchema(BaseModel):
    url: str
    title: str = "Browser Page"
    dom_snippet: str = ""
    interactive_elements: List[Dict[str, str]] = Field(default_factory=list)
    text_content: str = ""
    retrieved_at: float = Field(default_factory=time.time)
    permission_status: str = "READ_ONLY"


# -------------------------
# COMPUTER CONTROLLER SCHEMAS
# -------------------------
class ComputerActionSchema(BaseModel):
    action_type: str = "INSPECT_WORKSPACE"  # READ_FILE, INSPECT_WORKSPACE, EDIT_FILE
    target_path: Optional[str] = None
    command: Optional[str] = None


class ComputerRiskSchema(BaseModel):
    risk_level: str = "RISK_LOW"  # RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_PROHIBITED"
    is_sandboxed: bool = True
    reason: str = "Workspace sandboxed operation"


class ComputerObservationSchema(BaseModel):
    action_type: str
    target_path: str = ""
    content_snippet: str = ""
    file_count: int = 0
    risk_level: str = "RISK_LOW"
    retrieved_at: float = Field(default_factory=time.time)


# -------------------------
# DEVELOPMENT CAPABILITY SCHEMAS
# -------------------------
class RepositoryContextSchema(BaseModel):
    repository_id: str = "saki"
    root_path: str = r"c:\Users\gurus\work\saki"
    project_type: str = "Python/FastAPI + TypeScript/React"
    languages: List[str] = Field(default_factory=lambda: ["Python", "TypeScript", "HTML", "CSS"])
    frameworks: List[str] = Field(default_factory=lambda: ["FastAPI", "React", "Pydantic", "Pytest"])
    source_directories: List[str] = Field(default_factory=lambda: ["backend", "frontend/src"])
    test_directories: List[str] = Field(default_factory=lambda: ["backend/tests", "brain/tests"])
    git_branch: str = "main"


class ChangeProposalSchema(BaseModel):
    change_id: str
    target_file: str
    operation: str = "MODIFY"  # CREATE, MODIFY, RENAME, DELETE
    reason: str = ""
    risk_level: str = "LOW"    # READ_ONLY, LOW, MEDIUM, HIGH, CRITICAL
    diff_snippet: str = ""


class DevelopmentTaskSchema(BaseModel):
    task_id: str
    user_request: str
    objective: str
    status: str = "COMPLETED"  # ANALYZING, PLANNING, MODIFYING, TESTING, VERIFYING, COMPLETED, FAILED, BLOCKED
    files_changed: List[str] = Field(default_factory=list)
    tests_run: int = 0
    tests_passed: bool = True
    summary: str = ""


# -------------------------
# GIT & GITHUB CAPABILITY SCHEMAS
# -------------------------
class GitStatusSchema(BaseModel):
    current_branch: str = "main"
    is_clean: bool = True
    staged_files: List[str] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    untracked_files: List[str] = Field(default_factory=list)


class IssueSchema(BaseModel):
    issue_number: int = 1
    title: str = "Issue Title"
    author: str = "user"
    body_snippet: str = ""
    status: str = "OPEN"


class PullRequestSchema(BaseModel):
    pr_number: int = 1
    title: str = "Draft PR Title"
    head_branch: str = "feature/task-1"
    base_branch: str = "main"
    is_draft: bool = True
    state: str = "DRAFT"


class GitGitHubTelemetrySchema(BaseModel):
    operation: str = "GIT_STATUS"
    repository: str = "dudyalagurusreekar/saki"
    branch: str = "main"
    status_state: str = "LOCAL_VERIFIED"
    details: str = "Git operation executed successfully."


# -------------------------
# PERSISTENT TASK SCHEMAS
# -------------------------
class SakiTaskSchema(BaseModel):
    task_id: str
    objective: str
    status: str = "CREATED"  # CREATED, PLANNED, WAITING, READY, RUNNING, PAUSED, COMPLETED, FAILED, EXPIRED, CANCELLED
    schedule_type: str = "ONE_TIME"  # ONE_TIME, RECURRING, CONDITION_BASED
    trigger_condition: Optional[str] = None
    capability_scope: List[str] = Field(default_factory=lambda: ["WEB_READ", "NOTIFICATION"])
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3


class TaskTelemetrySchema(BaseModel):
    action: str = "CREATE_TASK"
    task_id: str
    status: str = "ACTIVE"
    details: str = "Task operation completed."


# -------------------------
# PERSONAL CONTEXT SCHEMAS
# -------------------------
class PersonalContextItemSchema(BaseModel):
    context_id: str
    category: str = "PREFERENCE_CONTEXT"  # IDENTITY, PREFERENCE, GOAL, PROJECT, TASK, TEMPORARY
    content: str
    source: str = "USER_EXPLICIT"          # USER_EXPLICIT, USER_APPROVED, TASK_STATE, PROJECT_STATE, DERIVED
    confidence: str = "HIGH"               # HIGH, MEDIUM, LOW
    importance: str = "NORMAL"             # LOW, NORMAL, HIGH
    status: str = "ACTIVE"                 # ACTIVE, STALE, SUPERSEDED, EXPIRED, REVOKED


class GoalContextSchema(BaseModel):
    goal_id: str
    objective: str
    priority: str = "NORMAL"
    status: str = "ACTIVE"
    progress: float = 0.0


class PersonalContextTelemetrySchema(BaseModel):
    active_items_count: int = 0
    top_categories: List[str] = Field(default_factory=list)
    proactive_attention_mode: str = "SHOULD_WAIT"  # SHOULD_NOTIFY, SHOULD_WAIT, SHOULD_ASK, SHOULD_ACT, SHOULD_IGNORE
    details: str = "Personal context evaluated successfully."


# -------------------------
# UNIFIED KNOWLEDGE & RAG SCHEMAS
# -------------------------
class KnowledgeCandidateSchema(BaseModel):
    id: str
    source_type: str  # USER_MEMORY, PROJECT_STATE, LOCAL_DOCUMENT, CODE, GITHUB, WEB_SOURCE
    content: str
    location: str
    confidence: str = "HIGH"
    freshness: str = "CURRENT"
    relevance_score: float = 1.0
    provenance_label: str


class UnifiedKnowledgePackageSchema(BaseModel):
    total_candidates: int = 0
    sources_queried: List[str] = Field(default_factory=list)
    has_conflicts: bool = False
    candidates: List[KnowledgeCandidateSchema] = Field(default_factory=list)
    details: str = "Knowledge retrieval completed."


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
    evidence_package: Optional[EvidencePackageSchema] = None
    research_result: Optional[ResearchResultSchema] = None
    memory_admission: Optional[MemoryAdmissionDecisionSchema] = None
    browser_observation: Optional[BrowserObservationSchema] = None
    computer_observation: Optional[ComputerObservationSchema] = None
    development_task: Optional[DevelopmentTaskSchema] = None
    git_github_telemetry: Optional[GitGitHubTelemetrySchema] = None
    persistent_task: Optional[SakiTaskSchema] = None
    personal_context: Optional[PersonalContextTelemetrySchema] = None
    unified_knowledge: Optional[UnifiedKnowledgePackageSchema] = None














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
