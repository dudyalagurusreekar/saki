"""
Saki Privacy & Security Boundary — Outbound Data Protection Subsystem
Enforces deterministic executable Python security rules between Saki Internal World and External World.
Implements data classification, secret detection, PII sanitization, firewalls (Memory, Conversation, System Prompt, Attachment),
fail-closed policy evaluation, privacy modes, and safe structured audit logging.
"""

import re
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from backend.core.config import settings

# -------------------------
# DATA CLASSIFICATION CONSTANTS
# -------------------------
DATA_PUBLIC = "PUBLIC"           # Public technical facts, documentation, general concepts
DATA_CONTEXTUAL = "CONTEXTUAL"   # Project/tool names required for search (e.g. Python, FastAPI, RTX 5060)
DATA_PERSONAL = "PERSONAL"     # User name, email, phone, personal identifiers
DATA_PRIVATE = "PRIVATE"       # Private notes, conversation history, user memories, uploaded files
DATA_SECRET = "SECRET"         # API keys, tokens, passwords, private keys, auth cookies
DATA_RESTRICTED = "RESTRICTED" # Local file paths, system env vars, authenticated account data

ALL_DATA_CLASSIFICATIONS = [
    DATA_PUBLIC,
    DATA_CONTEXTUAL,
    DATA_PERSONAL,
    DATA_PRIVATE,
    DATA_SECRET,
    DATA_RESTRICTED
]

# -------------------------
# DECISION CONSTANTS
# -------------------------
DECISION_ALLOW = "ALLOW"
DECISION_SANITIZE = "SANITIZE"
DECISION_BLOCK = "BLOCK"
DECISION_REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"

POLICY_VERSION = "s2.1"


# -------------------------
# DATA MODELS
# -------------------------
class OutboundDataItem(BaseModel):
    value_descriptor: str = Field(description="Safe descriptor e.g. EMAIL, API_KEY, PUBLIC_QUERY")
    classification: str = Field(default=DATA_PUBLIC)
    source: str = Field(default="user_input")
    reason: str = Field(default="outbound_data_element")
    required_for_request: bool = True
    confidence: float = 1.0
    sensitivity: float = 0.0
    action: str = Field(default=DECISION_ALLOW)


class OutboundRequest(BaseModel):
    action: str = Field(default="WEB_SEARCH")
    destination: str = Field(default="PUBLIC_SEARCH")
    method: str = Field(default="GET")
    query: str = Field(default="")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, Any] = Field(default_factory=dict)
    data_items: List[OutboundDataItem] = Field(default_factory=list)
    requested_capability: str = Field(default="WEB_SEARCH")
    privacy_mode: str = Field(default="BALANCED")
    requires_confirmation: bool = False
    purpose: str = Field(default="outbound_search")


class PrivacyDecision(BaseModel):
    decision: str = Field(default=DECISION_BLOCK, description="ALLOW, SANITIZE, BLOCK, REQUIRE_CONFIRMATION")
    reason: str = Field(default="Fail-closed default evaluation")
    risk_level: str = Field(default="LOW", description="LOW, MEDIUM, HIGH, CRITICAL")
    sanitized_request: str = Field(default="")
    blocked_items: List[str] = Field(default_factory=list, description="Safe descriptors of blocked data e.g. ['API_KEY']")
    removed_items: List[str] = Field(default_factory=list, description="Safe descriptors of sanitized data e.g. ['EMAIL']")
    policy_version: str = Field(default=POLICY_VERSION)
    audit_id: str = Field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:8]}")


# -------------------------
# DETERMINISTIC REGEX DETECTORS
# -------------------------

# Secrets: API keys, JWT, Bearer tokens, private keys, passwords, credentials
SECRET_PATTERNS = [
    (r"AIzaSy[A-Za-z0-9_-]{33}", "GOOGLE_API_KEY"),
    (r"sk-[A-Za-z0-9_-]{20,}", "OPENAI_API_KEY"),
    (r"ghp_[A-Za-z0-9]{36}", "GITHUB_PAT"),
    (r"gho_[A-Za-z0-9]{36}", "GITHUB_OAUTH_TOKEN"),
    (r"glpat-[A-Za-z0-9_-]{20,}", "GITLAB_TOKEN"),
    (r"bearer\s+[A-Za-z0-9_\-\.]{20,}", "BEARER_TOKEN"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT_TOKEN"),
    (r"-----BEGIN (?:RSA |EC |PGP )?PRIVATE KEY-----", "PRIVATE_KEY"),
    (r"\b(password|passwd|pwd|secret_key|api_secret)\s*[:=]\s*[^\s,;]+", "PASSWORD_ASSIGNMENT"),
    (r"https?://[^:\s]+:[^@\s]+@[^\s]+", "URL_EMBEDDED_CREDENTIALS"),
    (r"\b(authorization|auth_token)\s*[:=]\s*[^\s,;]+", "AUTH_HEADER_DATA")
]

# PII: Emails, Phone numbers, Credit Cards, IP addresses
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "PHONE_NUMBER"),
    (r"\b(?:\d[ -]*?){13,16}\b", "CREDIT_CARD_PATTERN")
]

# System prompt / internal leak indicators
SYSTEM_PROMPT_PATTERNS = [
    r"\[(?:Instruction|System|Developer|System Prompt|Developer Message)\]",
    r"You are Dr\. Elara",
    r"You are Saki",
    r"Anti-Assistant Rules:",
    r"Healthy Boundaries:"
]

# Conversation & Memory indicators
MEMORY_LEAK_PATTERNS = [
    r"\b(entire memory|all my memories|conversation history|my private notes|uploaded pdf content)\b"
]


# -------------------------
# PRIVACY POLICY ENGINE
# -------------------------
class PrivacyPolicyEngine:
    """
    Centralized Python Security Engine enforcing deterministic outbound privacy boundaries.
    """

    @staticmethod
    def detect_secrets(text: str) -> List[Tuple[str, str]]:
        """Scans text for hardcoded API keys, tokens, passwords, credentials."""
        found = []
        for pattern, descriptor in SECRET_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append((descriptor, pattern))
        return found

    @staticmethod
    def detect_pii(text: str) -> List[Tuple[str, str]]:
        """Scans text for personal identifiers like email, phone, credit cards."""
        found = []
        for pattern, descriptor in PII_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                found.append((descriptor, m.group(0)))
        return found

    @staticmethod
    def sanitize_query(raw_query: str) -> Tuple[str, List[str]]:
        """
        Strips PII and sensitive data while preserving technical context.
        Returns (sanitized_text, list_of_removed_descriptors).
        """
        if not raw_query or len(raw_query.strip()) == 0:
            return "", []

        cleaned = raw_query
        removed_descriptors = []

        # 1. Remove emails
        email_matches = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", cleaned)
        if email_matches:
            cleaned = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "", cleaned)
            removed_descriptors.append("EMAIL")

        # 2. Remove phone numbers
        phone_matches = re.findall(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", cleaned)
        if phone_matches:
            cleaned = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "", cleaned)
            removed_descriptors.append("PHONE_NUMBER")

        # 3. Clean up extra spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned, removed_descriptors

    @classmethod
    def evaluate_request(
        cls,
        request: OutboundRequest,
        privacy_mode: Optional[str] = None
    ) -> PrivacyDecision:
        """
        Evaluates OutboundRequest against security policies.
        ALWAYS FAILS CLOSED ON ERROR OR UNCERTAINTY.
        """
        try:
            mode = (privacy_mode or request.privacy_mode or settings.PRIVACY_MODE).upper()
            raw_query = (request.query or "").strip()
            
            # --- FAIL CLOSED RULE 1: HIGH / STRICT Privacy Mode ---
            if mode in ["HIGH", "STRICT"]:
                return PrivacyDecision(
                    decision=DECISION_BLOCK,
                    reason=f"Privacy mode '{mode}' blocks all outbound network requests.",
                    risk_level="LOW",
                    sanitized_request="",
                    blocked_items=["OUTBOUND_NETWORK_DISABLED"],
                    policy_version=POLICY_VERSION
                )

            # --- FAIL CLOSED RULE 2: Check for Secrets ---
            detected_secrets = cls.detect_secrets(raw_query)
            if detected_secrets:
                secret_descriptors = list(set(desc for desc, _ in detected_secrets))
                return PrivacyDecision(
                    decision=DECISION_BLOCK,
                    reason=f"Outbound request contains detected secrets/credentials: {', '.join(secret_descriptors)}",
                    risk_level="CRITICAL",
                    sanitized_request="",
                    blocked_items=secret_descriptors,
                    policy_version=POLICY_VERSION
                )

            # --- FAIL CLOSED RULE 3: System Prompt / Memory / Conversation Firewalls ---
            if any(re.search(pat, raw_query, re.IGNORECASE) for pat in SYSTEM_PROMPT_PATTERNS):
                return PrivacyDecision(
                    decision=DECISION_BLOCK,
                    reason="Outbound request contains system prompt instructions or internal identity text.",
                    risk_level="HIGH",
                    sanitized_request="",
                    blocked_items=["SYSTEM_PROMPT"],
                    policy_version=POLICY_VERSION
                )

            if any(re.search(pat, raw_query, re.IGNORECASE) for pat in MEMORY_LEAK_PATTERNS):
                return PrivacyDecision(
                    decision=DECISION_BLOCK,
                    reason="Outbound request attempts to exfiltrate bulk conversation memory or private attachments.",
                    risk_level="HIGH",
                    sanitized_request="",
                    blocked_items=["PRIVATE_MEMORY_EXFILTRATION"],
                    policy_version=POLICY_VERSION
                )

            # --- RULE 4: Sanitize PII ---
            sanitized, removed_items = cls.sanitize_query(raw_query)

            # --- FAIL CLOSED RULE 5: Empty / Ambiguous Sanitized Query ---
            if len(sanitized) < 3:
                return PrivacyDecision(
                    decision=DECISION_BLOCK,
                    reason="Sanitized query is empty or too short after removing sensitive elements.",
                    risk_level="MEDIUM",
                    sanitized_request="",
                    blocked_items=removed_items or ["EMPTY_QUERY"],
                    removed_items=removed_items,
                    policy_version=POLICY_VERSION
                )

            # --- RULE 6: Allow or Sanitize Decision ---
            decision_type = DECISION_SANITIZE if removed_items else DECISION_ALLOW
            reason_msg = f"Query sanitized (removed {', '.join(removed_items)})" if removed_items else "Query validated as privacy-safe."

            return PrivacyDecision(
                decision=decision_type,
                reason=reason_msg,
                risk_level="LOW" if decision_type == DECISION_ALLOW else "MEDIUM",
                sanitized_request=sanitized,
                removed_items=removed_items,
                policy_version=POLICY_VERSION
            )

        except Exception as e:
            # ABSOLUTE RULE 1 — FAIL CLOSED ON ANY ENGINE ERROR
            return PrivacyDecision(
                decision=DECISION_BLOCK,
                reason=f"Fail-closed evaluation triggered by security engine exception: {str(e)}",
                risk_level="CRITICAL",
                sanitized_request="",
                blocked_items=["SECURITY_ENGINE_ERROR"],
                policy_version=POLICY_VERSION
            )


# -------------------------
# SAFE AUDIT LOGGER
# -------------------------
class PrivacyAuditLogger:
    """
    Emits structured security audit logs using safe descriptors without exposing secrets or PII.
    """

    @staticmethod
    def log_decision(decision: PrivacyDecision, action: str = "WEB_SEARCH", destination: str = "PUBLIC_SEARCH") -> Dict[str, Any]:
        audit_event = {
            "timestamp": time.time(),
            "audit_id": decision.audit_id,
            "action": action,
            "decision": decision.decision,
            "risk_level": decision.risk_level,
            "destination": destination,
            "blocked_count": len(decision.blocked_items),
            "removed_count": len(decision.removed_items),
            "blocked_descriptors": decision.blocked_items,
            "removed_descriptors": decision.removed_items,
            "policy_version": decision.policy_version
        }
        # In production, write to audit event stream or secure logger
        return audit_event


# -------------------------
# BACKWARD COMPATIBILITY HELPERS
# -------------------------
def make_safe_query(user_input: str) -> str:
    """
    Transforms user input into a neutral, privacy-safe search query.
    Enforces deterministic Python security boundary before any LLM execution.
    """
    req = OutboundRequest(query=user_input, action="WEB_SEARCH")
    decision = PrivacyPolicyEngine.evaluate_request(req)
    
    if decision.decision in [DECISION_BLOCK, DECISION_REQUIRE_CONFIRMATION]:
        return ""
        
    return decision.sanitized_request or user_input.strip()


def expand_query(query: str) -> List[str]:
    """
    Expands query into 1-2 search variations if query passes privacy gate.
    """
    safe = make_safe_query(query)
    if not safe:
        return []
    return [safe]