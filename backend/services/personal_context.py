"""
Saki Integrated Personal Context & Proactive Assistance Subsystem (PersonalContextEngine)
Provides structured personal context understanding, context relevance ranking, minimal context budgeting,
provenance tracking, conflict resolution, user-controlled revocation (forget), and proactive AttentionPolicy.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.memory_admission import MemoryAdmissionEngine, MemoryCandidate, SOURCE_USER, TYPE_PERSONAL_MEMORY

# Context Categories
CAT_IDENTITY = "IDENTITY_CONTEXT"
CAT_PREFERENCE = "PREFERENCE_CONTEXT"
CAT_GOAL = "GOAL_CONTEXT"
CAT_PROJECT = "PROJECT_CONTEXT"
CAT_TASK = "TASK_CONTEXT"
CAT_ROUTINE = "ROUTINE_CONTEXT"
CAT_COMMITMENT = "COMMITMENT_CONTEXT"
CAT_RELATIONSHIP = "RELATIONSHIP_CONTEXT"
CAT_TEMPORARY = "TEMPORARY_CONTEXT"

# Context Sources
SOURCE_USER_EXPLICIT = "USER_EXPLICIT"
SOURCE_USER_APPROVED = "USER_APPROVED"
SOURCE_TASK_STATE = "TASK_STATE"
SOURCE_PROJECT_STATE = "PROJECT_STATE"
SOURCE_DERIVED = "DERIVED"
SOURCE_SYSTEM_OBSERVATION = "SYSTEM_OBSERVATION"

# Context Statuses
STATUS_ACTIVE = "ACTIVE"
STATUS_STALE = "STALE"
STATUS_SUPERSEDED = "SUPERSEDED"
STATUS_EXPIRED = "EXPIRED"
STATUS_REVOKED = "REVOKED"

# Confidence & Importance
CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

IMPORTANCE_LOW = "LOW"
IMPORTANCE_NORMAL = "NORMAL"
IMPORTANCE_HIGH = "HIGH"

# Attention Modes
MODE_SHOULD_NOTIFY = "SHOULD_NOTIFY"
MODE_SHOULD_WAIT = "SHOULD_WAIT"
MODE_SHOULD_ASK = "SHOULD_ASK"
MODE_SHOULD_ACT = "SHOULD_ACT"
MODE_SHOULD_IGNORE = "SHOULD_IGNORE"

# Budget Limits
MAX_CONTEXT_ITEMS = 5
MAX_CONTEXT_TOKENS = 500


# -------------------------
# DATA MODELS
# -------------------------
class PersonalContextItem(BaseModel):
    context_id: str = Field(default_factory=lambda: f"ctx-{time.time_ns() % 1000000}")
    category: str = CAT_PREFERENCE
    content: str
    source: str = SOURCE_USER_EXPLICIT
    confidence: str = CONFIDENCE_HIGH
    importance: str = IMPORTANCE_NORMAL
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    last_used: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    provenance: str = "User explicit statement"
    status: str = STATUS_ACTIVE


class GoalContext(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal-{time.time_ns() % 1000000}")
    objective: str
    priority: str = IMPORTANCE_NORMAL
    status: str = STATUS_ACTIVE
    progress: float = 0.0
    related_projects: List[str] = Field(default_factory=list)


class AttentionPolicy(BaseModel):
    proactive_level: str = "NORMAL"  # OFF, LOW, NORMAL, HIGH
    notification_preference: str = "important-only"  # silent, in-app, important-only, all
    quiet_period_active: bool = False


# -------------------------
# PERSONAL CONTEXT ENGINE
# -------------------------
class PersonalContextEngine:
    """
    Native Personal Context Engine implementing minimal context selection,
    provenance tracking, conflict resolution, user forget, and AttentionPolicy evaluation.
    """

    _context_store: Dict[str, PersonalContextItem] = {}

    @classmethod
    def initialize_defaults(cls):
        if not cls._context_store:
            cls.add_item(PersonalContextItem(
                category=CAT_PROJECT,
                content="User is developing Saki AI project (FastAPI + React)",
                source=SOURCE_USER_EXPLICIT,
                importance=IMPORTANCE_HIGH
            ))
            cls.add_item(PersonalContextItem(
                category=CAT_PREFERENCE,
                content="User prefers concise, direct responses with precise code snippets",
                source=SOURCE_USER_EXPLICIT,
                importance=IMPORTANCE_NORMAL
            ))

    @classmethod
    def add_item(cls, item: PersonalContextItem) -> PersonalContextItem:
        # Memory Poisoning Guard: Derived/Web sources cannot create HIGH confidence user preferences
        if item.source in [SOURCE_DERIVED, "WEB"] and item.category in [CAT_PREFERENCE, CAT_IDENTITY]:
            item.confidence = CONFIDENCE_LOW
            item.source = SOURCE_DERIVED

        cls._context_store[item.context_id] = item
        return item

    @classmethod
    def select_minimal_context(cls, query: str, max_items: int = MAX_CONTEXT_ITEMS) -> List[PersonalContextItem]:
        cls.initialize_defaults()
        query_lower = query.lower()
        active_items = [item for item in cls._context_store.values() if item.status == STATUS_ACTIVE]

        # Score items by recency, importance, and query relevance
        scored_items = []
        for item in active_items:
            score = 1.0
            if item.importance == IMPORTANCE_HIGH:
                score += 2.0
            if item.source == SOURCE_USER_EXPLICIT:
                score += 1.5
            if any(w in query_lower for w in item.content.lower().split()):
                score += 3.0
            scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        selected = [item for _, item in scored_items[:max_items]]

        for s in selected:
            s.last_used = time.time()

        return selected

    @classmethod
    def resolve_conflict(cls, category: str, new_content: str) -> PersonalContextItem:
        """
        Supersedes outdated context items in the same category when user provides authoritative updates.
        """
        for item in cls._context_store.values():
            if item.category == category and item.status == STATUS_ACTIVE:
                item.status = STATUS_SUPERSEDED
                item.updated_at = time.time()

        new_item = PersonalContextItem(
            category=category,
            content=new_content,
            source=SOURCE_USER_EXPLICIT,
            status=STATUS_ACTIVE
        )
        return cls.add_item(new_item)

    @classmethod
    def forget_context(cls, keyword: str) -> int:
        """
        User-controlled forget: Revokes and marks matching context items as REVOKED.
        """
        forgotten_count = 0
        kw_lower = keyword.lower()
        for item in cls._context_store.values():
            if kw_lower in item.content.lower() and item.status == STATUS_ACTIVE:
                item.status = STATUS_REVOKED
                item.updated_at = time.time()
                forgotten_count += 1
        return forgotten_count

    @classmethod
    def evaluate_proactive_attention(cls, policy: AttentionPolicy, event_importance: str = IMPORTANCE_NORMAL) -> str:
        """
        Evaluates AttentionPolicy to decide: SHOULD_NOTIFY, SHOULD_WAIT, SHOULD_ASK, SHOULD_ACT, SHOULD_IGNORE.
        """
        if policy.proactive_level == "OFF":
            return MODE_SHOULD_IGNORE

        if policy.quiet_period_active and event_importance != IMPORTANCE_HIGH:
            return MODE_SHOULD_WAIT

        if event_importance == IMPORTANCE_HIGH:
            return MODE_SHOULD_NOTIFY

        if policy.proactive_level in ["NORMAL", "HIGH"]:
            return MODE_SHOULD_NOTIFY

        return MODE_SHOULD_WAIT
