"""
Saki Memory Admission Engine & World Knowledge Integration Subsystem
Evaluates memory candidates, enforces privacy/security admission boundaries,
prevents memory poisoning attacks from external web content, and manages memory lifecycle.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK

# -------------------------
# MEMORY TAXONOMY
# -------------------------
TYPE_CONVERSATION = "CONVERSATION_MEMORY"
TYPE_WORKING = "WORKING_MEMORY"
TYPE_PERSONAL = "PERSONAL_MEMORY"
TYPE_PERSONAL_MEMORY = "PERSONAL_MEMORY"
TYPE_PROJECT = "PROJECT_MEMORY"
TYPE_PROJECT_MEMORY = "PROJECT_MEMORY"
TYPE_PREFERENCE = "PREFERENCE_MEMORY"
TYPE_PREFERENCE_MEMORY = "PREFERENCE_MEMORY"
TYPE_TASK = "TASK_MEMORY"
TYPE_LOCAL_KNOWLEDGE = "LOCAL_KNOWLEDGE"
TYPE_WEB_EVIDENCE = "WEB_EVIDENCE"
TYPE_VERIFIED_WORLD = "VERIFIED_WORLD_KNOWLEDGE"


# Lifecycle Status
STATUS_CANDIDATE = "CANDIDATE"
STATUS_EVALUATING = "EVALUATING"
STATUS_ADMITTED = "ADMITTED"
STATUS_ACTIVE = "ACTIVE"
STATUS_AGING = "AGING"
STATUS_STALE = "STALE"
STATUS_ARCHIVED = "ARCHIVED"
STATUS_FORGOTTEN = "FORGOTTEN"

# Knowledge Status
KNOWLEDGE_UNVERIFIED = "UNVERIFIED"
KNOWLEDGE_SUPPORTED = "SUPPORTED"
KNOWLEDGE_VERIFIED = "VERIFIED"
KNOWLEDGE_STALE = "STALE"
KNOWLEDGE_CONFLICTED = "CONFLICTED"
KNOWLEDGE_SUPERSEDED = "SUPERSEDED"

# Decisions
ADMIT_DECISION_ADMIT = "ADMIT"
ADMIT_DECISION_REJECT = "REJECT"
ADMIT_DECISION_DEFER = "DEFER"
ADMIT_DECISION_CONFIRM = "REQUIRE_CONFIRMATION"

# Expiration Policies
EXPIRATION_EPHEMERAL = "EPHEMERAL"           # Minutes / Request lifetime
EXPIRATION_CURRENT = "CURRENT"               # Days / Months
EXPIRATION_STABLE = "STABLE"                 # Years
EXPIRATION_PERMANENT = "PERMANENT_USER_FACT" # Indefinite until user forgets

# Source Types
SOURCE_USER = "USER"
SOURCE_CONVERSATION = "CONVERSATION"
SOURCE_LOCAL_DOC = "LOCAL_DOCUMENT"
SOURCE_RAG = "RAG"
SOURCE_WEB = "WEB"
SOURCE_RESEARCH = "RESEARCH"
SOURCE_SYSTEM = "SYSTEM"


# -------------------------
# DATA MODELS
# -------------------------
class MemoryCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"cand-{time.time_ns() % 1000000}")
    content: str
    memory_type: str = Field(default=TYPE_WEB_EVIDENCE)
    source_type: str = Field(default=SOURCE_WEB)
    source_id: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.90)
    relevance: float = Field(default=0.90)
    importance: str = Field(default="NORMAL")  # LOW, NORMAL, HIGH
    temporal_scope: str = Field(default="CURRENT")
    privacy_classification: str = Field(default="PUBLIC")
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
    admission_reason: Optional[str] = None


class MemoryAdmissionDecision(BaseModel):
    decision: str = Field(default=ADMIT_DECISION_REJECT)
    reason: str
    memory_type: str = Field(default=TYPE_WEB_EVIDENCE)
    confidence: float = Field(default=0.90)
    importance: str = Field(default="NORMAL")
    expiration: str = Field(default=EXPIRATION_EPHEMERAL)
    conflict_status: str = Field(default="NO_CONFLICT")


class MemoryConflict(BaseModel):
    conflict_id: str = Field(default_factory=lambda: f"memcfl-{time.time_ns() % 1000000}")
    memory_id: str
    old_value: str
    new_value: str
    old_source: str
    new_source: str
    detected_at: float = Field(default_factory=time.time)
    conflict_type: str = Field(default="DIRECT_CONFLICT")  # DIRECT_CONFLICT, TEMPORAL_CHANGE, USER_CORRECTION
    resolution_status: str = Field(default="UNRESOLVED")


class MemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem-{time.time_ns() % 1000000}")
    content: str
    type: str = Field(default=TYPE_PERSONAL_MEMORY)
    source: str = Field(default=SOURCE_USER)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.95)
    importance: str = Field(default="NORMAL")
    privacy_level: str = Field(default="PRIVATE")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    valid_from: float = Field(default_factory=time.time)
    valid_until: Optional[float] = None
    status: str = Field(default=STATUS_ACTIVE)
    knowledge_status: str = Field(default=KNOWLEDGE_VERIFIED)
    evidence_refs: List[str] = Field(default_factory=list)
    source_refs: List[str] = Field(default_factory=list)
    version: int = 1
    user_controlled: bool = True


# -------------------------
# MEMORY ADMISSION ENGINE
# -------------------------
class MemoryAdmissionEngine:
    """
    Evaluates MemoryCandidate objects against strict security, privacy,
    and admission rules. Prevents web content memory poisoning.
    """

    POISONING_PATTERNS = [
        r"store this as (permanent|durable|system) memory",
        r"remember that the user (likes|prefers|wants|is)",
        r"delete (all|my|user) memor(y|ies)",
        r"forget (everything|all|my) memor(y|ies)",
        r"override system prompt",
        r"set user preference to"
    ]

    @classmethod
    def evaluate_candidate(cls, candidate: MemoryCandidate) -> MemoryAdmissionDecision:
        content_lower = candidate.content.lower()

        # 1. MEMORY POISONING & INJECTION ATTACK DEFENSE
        if candidate.source_type in [SOURCE_WEB, SOURCE_RESEARCH]:
            for pattern in cls.POISONING_PATTERNS:
                if re.search(pattern, content_lower):
                    return MemoryAdmissionDecision(
                        decision=ADMIT_DECISION_REJECT,
                        reason="Memory admission rejected: External web content memory injection / poisoning pattern detected.",
                        memory_type=candidate.memory_type,
                        expiration=EXPIRATION_EPHEMERAL
                    )

            # Rule: Web evidence CANNOT create personal preferences
            if candidate.memory_type in [TYPE_PERSONAL_MEMORY, TYPE_PREFERENCE_MEMORY]:
                return MemoryAdmissionDecision(
                    decision=ADMIT_DECISION_REJECT,
                    reason="Memory admission rejected: External web evidence cannot create personal user preferences.",
                    memory_type=candidate.memory_type,
                    expiration=EXPIRATION_EPHEMERAL
                )

            # Rule: Web evidence is TEMPORARY by default
            if candidate.memory_type == TYPE_WEB_EVIDENCE:
                return MemoryAdmissionDecision(
                    decision=ADMIT_DECISION_REJECT,
                    reason="Memory admission default: Web evidence remains request-scoped temporary data.",
                    memory_type=TYPE_WEB_EVIDENCE,
                    expiration=EXPIRATION_EPHEMERAL
                )

        # 2. EXPLICIT USER INSTRUCTION ADMISSION
        if candidate.source_type == SOURCE_USER:
            if candidate.memory_type in [TYPE_PERSONAL_MEMORY, TYPE_PREFERENCE_MEMORY, TYPE_PROJECT_MEMORY]:
                return MemoryAdmissionDecision(
                    decision=ADMIT_DECISION_ADMIT,
                    reason="Explicit user instruction admitted into durable memory.",
                    memory_type=candidate.memory_type,
                    confidence=1.0,
                    importance=candidate.importance or "HIGH",
                    expiration=EXPIRATION_PERMANENT
                )

        # 3. VERIFIED WORLD KNOWLEDGE PROMOTION
        if candidate.source_type in [SOURCE_WEB, SOURCE_RESEARCH] and candidate.memory_type == TYPE_VERIFIED_WORLD:
            if candidate.confidence >= 0.95 and candidate.source_id:
                return MemoryAdmissionDecision(
                    decision=ADMIT_DECISION_ADMIT,
                    reason="Verified primary web evidence promoted to durable world knowledge.",
                    memory_type=TYPE_VERIFIED_WORLD,
                    confidence=candidate.confidence,
                    importance="NORMAL",
                    expiration=EXPIRATION_STABLE
                )

        # Default Safety Fallback: REJECT
        return MemoryAdmissionDecision(
            decision=ADMIT_DECISION_REJECT,
            reason="Candidate did not meet durable memory admission criteria.",
            memory_type=candidate.memory_type,
            expiration=EXPIRATION_EPHEMERAL
        )


# -------------------------
# MEMORY CONTEXT SELECTOR
# -------------------------
class MemoryContextSelector:
    """
    Ranks, filters, and formats memory context for outbound LLM prompts
    while enforcing privacy boundaries and preventing secret leakage.
    """

    @staticmethod
    def select_safe_context(memories: List[Dict[str, Any]], query: str, limit: int = 5) -> str:
        if not memories:
            return ""

        safe_blocks = []
        for mem in memories[:limit]:
            content = mem.get("content", "")
            m_type = mem.get("type", "GENERAL")
            
            # Check secret safety via Privacy Engine rules
            outbound_test = OutboundRequest(
                action="MEMORY_RECALL",
                destination="LOCAL_LLM",
                query=content,
                privacy_mode="BALANCED"
            )
            decision = PrivacyPolicyEngine.evaluate_request(outbound_test)
            if decision.decision == DECISION_BLOCK:
                continue  # Skip secret-bearing memories

            safe_blocks.append(f"- [{m_type}] {content}")

        if not safe_blocks:
            return ""

        return "\nRetrieved Active Memory:\n" + "\n".join(safe_blocks)
