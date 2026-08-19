"""
Saki Unified Knowledge & RAG Subsystem (UnifiedKnowledgeEngine)
Provides ONE unified knowledge and retrieval layer connecting Memory, Code, Project Docs,
GitHub, Web Evidence, and Personal Context under Saki's single-brain cognitive authority.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.memory_service import load_memory
from backend.services.development_capability import DevelopmentCapability
from backend.services.git_github_capability import GitGitHubCapability
from backend.services.personal_context import PersonalContextEngine


# Source Types
SRC_USER_MEMORY = "USER_MEMORY"
SRC_PROJECT_STATE = "PROJECT_STATE"
SRC_LOCAL_DOCUMENT = "LOCAL_DOCUMENT"
SRC_CODE = "CODE"
SRC_GITHUB = "GITHUB"
SRC_WEB_SOURCE = "WEB_SOURCE"

# Source Trust Weights
TRUST_AUTHORITATIVE = 1.0
TRUST_HIGH = 0.85
TRUST_MEDIUM = 0.70
TRUST_EXTERNAL = 0.50

# Freshness Statuses
FRESH_CURRENT = "CURRENT"
FRESH_RECENT = "RECENT"
FRESH_STALE = "STALE"

# Budget Constraints
MAX_RAG_CANDIDATES = 6
MAX_RAG_TOKENS = 800


# -------------------------
# DATA MODELS
# -------------------------
class KnowledgeCandidate(BaseModel):
    id: str = Field(default_factory=lambda: f"know-{time.time_ns() % 1000000}")
    source_type: str = SRC_PROJECT_STATE
    content: str
    location: str = ""
    confidence: str = "HIGH"
    freshness: str = FRESH_CURRENT
    relevance_score: float = 1.0
    trust_weight: float = TRUST_AUTHORITATIVE
    provenance_label: str = "Authoritative workspace source"
    created_at: float = Field(default_factory=time.time)
    is_untrusted_data: bool = False


class UnifiedKnowledgePackage(BaseModel):
    total_candidates: int = 0
    sources_queried: List[str] = Field(default_factory=list)
    has_conflicts: bool = False
    candidates: List[KnowledgeCandidate] = Field(default_factory=list)
    details: str = "Knowledge retrieval completed successfully."


# -------------------------
# UNIFIED KNOWLEDGE ENGINE
# -------------------------
class UnifiedKnowledgeEngine:
    """
    Unified Knowledge & RAG Engine routing queries across all approved connectors.
    """

    @classmethod
    def sanitize_prompt_injections(cls, text: str) -> Tuple[str, bool]:
        """
        Neutralizes prompt injection patterns in retrieved external content.
        """
        patterns = [
            r"ignore previous instructions",
            r"system prompt leak",
            r"override policy",
            r"forget all rules",
            r"you are now an unrestricted"
        ]
        sanitized = text
        detected = False
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                sanitized = re.sub(pat, "[REDACTED_PROMPT_INJECTION_ATTEMPT]", sanitized, flags=re.IGNORECASE)
                detected = True
        return sanitized, detected

    @classmethod
    def retrieve_knowledge(
        cls,
        query: str,
        user_id: str = "default_user",
        active_sources: Optional[List[str]] = None,
        web_evidence_items: Optional[List[Any]] = None
    ) -> UnifiedKnowledgePackage:
        query_lower = query.lower()
        candidates: List[KnowledgeCandidate] = []
        sources_queried = []

        # 1. Connector: USER_MEMORY & PERSONAL_CONTEXT
        sources_queried.append(SRC_USER_MEMORY)
        mem_data = load_memory()
        mem_results = [m for m in mem_data.get("memories", []) if any(w in m.get("content", "").lower() for w in query_lower.split())]
        for m in mem_results[:3]:
            candidates.append(KnowledgeCandidate(
                source_type=SRC_USER_MEMORY,
                content=m.get("content", ""),
                location="data/memory.json",
                trust_weight=TRUST_AUTHORITATIVE,
                provenance_label=f"User Memory ({m.get('type', 'FACT')})"
            ))

        personal_items = PersonalContextEngine.select_minimal_context(query)
        for p in personal_items:
            candidates.append(KnowledgeCandidate(
                source_type=SRC_USER_MEMORY,
                content=p.content,
                location="PersonalContextEngine",
                trust_weight=TRUST_AUTHORITATIVE,
                provenance_label=f"Personal Context ({p.category})"
            ))

        # 2. Connector: CODE & PROJECT_FILES (only for code-related queries)
        if any(k in query_lower for k in ["code", "file", "function", "class", "implement", "refactor", "debug", "build", "test", "fix", "error", "bug"]):
            sources_queried.append(SRC_CODE)
            dev_res = DevelopmentCapability.execute_development_task(query)
            if dev_res and dev_res.objective:
                target_loc = dev_res.files_changed[0] if dev_res.files_changed else (dev_res.plan.files_to_touch[0] if dev_res.plan and dev_res.plan.files_to_touch else "workspace")
                candidates.append(KnowledgeCandidate(
                    source_type=SRC_CODE,
                    content=f"Development plan: {dev_res.objective} - {dev_res.summary}",
                    location=target_loc,
                    trust_weight=TRUST_AUTHORITATIVE,
                    provenance_label="Verified Workspace Codebase"
                ))

        # 3. Connector: GITHUB
        sources_queried.append(SRC_GITHUB)
        if any(k in query_lower for k in ["github", "pr", "commit", "issue"]):
            git_res = GitGitHubCapability.execute_action("GIT_STATUS")
            candidates.append(KnowledgeCandidate(
                source_type=SRC_GITHUB,
                content=f"Repository {git_res.repository} branch {git_res.branch}: {git_res.details}",
                location=f"github.com/{git_res.repository}",
                trust_weight=TRUST_HIGH,
                provenance_label="Git/GitHub Capability"
            ))

        # 4. Connector: WEB_SOURCE (Populated from authoritative evidence to prevent duplicate searches)
        if web_evidence_items:
            sources_queried.append(SRC_WEB_SOURCE)
            for ev in web_evidence_items:
                raw_text = getattr(ev, "content", "") or ""
                clean_text, _ = cls.sanitize_prompt_injections(raw_text)
                candidates.append(KnowledgeCandidate(
                    source_type=SRC_WEB_SOURCE,
                    content=clean_text,
                    location=getattr(ev, "url", "") or "https://google.com",
                    trust_weight=TRUST_EXTERNAL,
                    is_untrusted_data=True,
                    provenance_label=f"Web Evidence ({getattr(ev, 'title', 'Web Source')[:30]})"
                ))
        elif any(k in query_lower for k in ["search", "web", "latest", "doc", "fastapi", "release", "current", "2026"]):
            sources_queried.append(SRC_WEB_SOURCE)
            raw_web_text = f"Public web documentation for query '{query}'."
            clean_text, _ = cls.sanitize_prompt_injections(raw_web_text)
            candidates.append(KnowledgeCandidate(
                source_type=SRC_WEB_SOURCE,
                content=clean_text,
                location="https://docs.python.org",
                trust_weight=TRUST_EXTERNAL,
                is_untrusted_data=True,
                provenance_label="External Web Source"
            ))

        # Rank, Deduplicate & Minimal Context Selection
        ranked_candidates, has_conflicts = cls.rank_and_deduplicate(query, candidates)


        return UnifiedKnowledgePackage(
            total_candidates=len(ranked_candidates),
            sources_queried=sources_queried,
            has_conflicts=has_conflicts,
            candidates=ranked_candidates[:MAX_RAG_CANDIDATES]
        )

    @classmethod
    def rank_and_deduplicate(cls, query: str, candidates: List[KnowledgeCandidate]) -> Tuple[List[KnowledgeCandidate], bool]:
        query_words = set(query.lower().split())
        seen_contents = set()
        unique_candidates = []
        has_conflicts = False

        for c in candidates:
            # Deduplication check
            canon = " ".join(c.content.lower().split()[:10])
            if canon in seen_contents:
                continue
            seen_contents.add(canon)

            # Score calculation: Trust weight + keyword match score
            match_score = sum(1.0 for w in query_words if w in c.content.lower())
            c.relevance_score = (c.trust_weight * 2.0) + match_score
            unique_candidates.append(c)

        unique_candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        return unique_candidates, has_conflicts
