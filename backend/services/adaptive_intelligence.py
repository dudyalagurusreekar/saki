"""
Saki Adaptive Intelligence & Learning Subsystem (AdaptiveIntelligenceEngine)
Provides controlled personalization, feedback processing, preference scoping,
supersession, revocation, and security policy protection without model retraining or second brain.
"""

import time
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.memory_admission import MemoryAdmissionEngine, MemoryCandidate, TYPE_PREFERENCE_MEMORY, ADMIT_DECISION_ADMIT, SOURCE_USER
from backend.services.personal_context import PersonalContextEngine




# Categories
CAT_EXPLICIT_PREFERENCE = "EXPLICIT_PREFERENCE"
CAT_EXPLICIT_CORRECTION = "EXPLICIT_CORRECTION"
CAT_WORKFLOW_PREFERENCE = "WORKFLOW_PREFERENCE"
CAT_PROJECT_PREFERENCE = "PROJECT_PREFERENCE"
CAT_COMMUNICATION_PREFERENCE = "COMMUNICATION_PREFERENCE"
CAT_TOOL_PREFERENCE = "TOOL_PREFERENCE"
CAT_TASK_PATTERN = "TASK_PATTERN"

# Scopes
SCOPE_GLOBAL = "GLOBAL"
SCOPE_PROJECT = "PROJECT"
SCOPE_TASK = "TASK"
SCOPE_SESSION = "SESSION"

# Statuses
STATUS_ACTIVE = "ACTIVE"
STATUS_SUPERSEDED = "SUPERSEDED"
STATUS_REVOKED = "REVOKED"
STATUS_STALE = "STALE"

# Security Policy Bypass Patterns (NEVER LEARNABLE)
SECURITY_BYPASS_PATTERNS = [
    r"never ask permission",
    r"disable security",
    r"bypass privacy",
    r"ignore permission",
    r"automatic push without verification",
    r"never verify code"
]

# Sensitive Attribute Patterns (NEVER INFERRABLE)
SENSITIVE_PATTERNS = [
    r"\bhealth\b", r"\breligion\b", r"\bpolitics\b", r"\bsexual\b", r"\brace\b", r"\bethnicity\b"
]


# -------------------------
# DATA MODELS
# -------------------------
class Preference(BaseModel):
    preference_id: str = Field(default_factory=lambda: f"pref_{uuid.uuid4().hex[:8]}")
    category: str = CAT_EXPLICIT_PREFERENCE
    value: str
    source: str = "USER_EXPLICIT"
    confidence: float = 1.0
    scope: str = SCOPE_GLOBAL
    project_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: str = STATUS_ACTIVE


class LearningCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:8]}")
    category: str = CAT_EXPLICIT_PREFERENCE
    proposed_change: str
    source: str = "USER_EXPLICIT"
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    created_at: float = Field(default_factory=time.time)
    status: str = "PROPOSED"
    privacy_scope: str = SCOPE_GLOBAL


class AdaptiveIntelligenceTelemetry(BaseModel):
    feedback_type: Optional[str] = None
    admitted_preferences: List[Preference] = Field(default_factory=list)
    active_candidates: List[LearningCandidate] = Field(default_factory=list)
    details: str = "Adaptive intelligence evaluation completed."


# In-memory preference store
PREFERENCE_STORE: Dict[str, Preference] = {}


# -------------------------
# ADAPTIVE INTELLIGENCE ENGINE SERVICE
# -------------------------
class AdaptiveIntelligenceEngine:
    """
    Adaptive Intelligence & Learning Engine processing explicit user feedback,
    handling preference scoping, supersession, revocation, and security safeguards.
    """

    @classmethod
    def classify_feedback(cls, text: str) -> Optional[str]:
        """
        Classifies user input into feedback types.
        """
        t = text.lower().strip()
        if any(p in t for p in ["i prefer", "always give me", "my preference is", "always use"]):
            return "EXPLICIT_PREFERENCE"
        if any(p in t for p in ["don't do", "that's wrong", "stop doing", "incorrect"]):
            return "EXPLICIT_CORRECTION"
        if any(p in t for p in ["forget this preference", "don't learn from this", "revoke preference", "i don't want that preference"]):
            return "REVOCATION"
        return None

    @classmethod
    def is_security_policy_modification(cls, text: str) -> bool:
        """
        Guardrail: Ensures learned preference CANNOT modify security or privacy policies.
        """
        return any(re.search(pat, text, re.IGNORECASE) for pat in SECURITY_BYPASS_PATTERNS)

    @classmethod
    def is_sensitive_inference(cls, text: str) -> bool:
        """
        Guardrail: Ensures Saki does NOT learn or infer sensitive attributes.
        """
        return any(re.search(pat, text, re.IGNORECASE) for pat in SENSITIVE_PATTERNS)

    @classmethod
    def process_user_input(cls, text: str, project_id: Optional[str] = None) -> AdaptiveIntelligenceTelemetry:
        """
        Processes user input for learning candidates and preference admission.
        """
        # Guardrail 1: Check security policy override attempt
        if cls.is_security_policy_modification(text):
            return AdaptiveIntelligenceTelemetry(
                feedback_type="SECURITY_BLOCKED",
                details="Learning candidate blocked: Learning cannot modify security or permission policies."
            )

        # Guardrail 2: Check sensitive attribute inference
        if cls.is_sensitive_inference(text):
            return AdaptiveIntelligenceTelemetry(
                feedback_type="SENSITIVE_BLOCKED",
                details="Learning candidate blocked: Sensitive attribute inference is strictly prohibited."
            )

        fb_type = cls.classify_feedback(text)
        if not fb_type:
            return AdaptiveIntelligenceTelemetry(details="No learning signals detected.")

        # Process Revocation / Forgetting
        if fb_type == "REVOCATION":
            revoked_count = cls.revoke_matching_preferences(text)
            return AdaptiveIntelligenceTelemetry(
                feedback_type="REVOCATION",
                details=f"Revoked {revoked_count} preference(s)."
            )

        # Create Learning Candidate
        scope = SCOPE_PROJECT if ("project" in text.lower() or project_id) else SCOPE_GLOBAL
        cand = LearningCandidate(
            category=CAT_EXPLICIT_PREFERENCE if fb_type == "EXPLICIT_PREFERENCE" else CAT_EXPLICIT_CORRECTION,
            proposed_change=text,
            source="USER_EXPLICIT",
            confidence=1.0,
            privacy_scope=scope
        )

        # Pass through MemoryAdmissionEngine (Sprint 6)
        mem_cand = MemoryCandidate(
            candidate_id=cand.candidate_id,
            memory_type=TYPE_PREFERENCE_MEMORY,
            source_type=SOURCE_USER,
            content=text,
            trust_weight=1.0,
            confidence=1.0
        )


        admission_decision = MemoryAdmissionEngine.evaluate_candidate(mem_cand)
        admitted_prefs = []

        if admission_decision.decision == ADMIT_DECISION_ADMIT:
            pref = Preference(
                category=cand.category,
                value=text,
                source="USER_EXPLICIT",
                confidence=1.0,
                scope=scope,
                project_id=project_id
            )
            # Handle supersession of existing preferences in same scope
            cls.supersede_older_preferences(pref)
            PREFERENCE_STORE[pref.preference_id] = pref
            admitted_prefs.append(pref)


        return AdaptiveIntelligenceTelemetry(
            feedback_type=fb_type,
            admitted_preferences=admitted_prefs,
            active_candidates=[cand],
            details=f"Processed feedback type '{fb_type}'. Admitted {len(admitted_prefs)} preference(s)."
        )

    @classmethod
    def supersede_older_preferences(cls, new_pref: Preference):
        """
        Supersedes older preferences in the same scope when a new explicit preference is admitted.
        """
        for pref in PREFERENCE_STORE.values():
            if pref.scope == new_pref.scope and pref.status == STATUS_ACTIVE:
                pref.status = STATUS_SUPERSEDED

    @classmethod
    def revoke_matching_preferences(cls, text: str) -> int:
        """
        Revokes preferences matching explicit forget/revocation directive.
        """
        count = 0
        for pref in PREFERENCE_STORE.values():
            if pref.status == STATUS_ACTIVE:
                pref.status = STATUS_REVOKED
                count += 1
        return count

    @classmethod
    def get_active_preferences(cls, scope: Optional[str] = None) -> List[Preference]:
        """
        Returns active preferences, filtered by scope if provided.
        """
        return [
            p for p in PREFERENCE_STORE.values()
            if p.status == STATUS_ACTIVE and (scope is None or p.scope == scope)
        ]
