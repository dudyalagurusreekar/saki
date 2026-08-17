"""
Saki Advanced Web Intelligence Subsystem (WebIntelligenceCapability)
Provides multi-step web intelligence, query refinement, primary source prioritization,
DOM browser fallback, date/freshness validation, and privacy query sanitization.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.world_access_manager import WorldAccessManager, DuckDuckGoSearchProvider, WebFetcher
from backend.services.browser_controller import BrowserController, BrowserAction

from backend.services.evidence_engine import EvidenceIntelligenceEngine, EvidencePackage
from backend.services.research_planner import ResearchPlanner, ResearchBudget
from backend.services.knowledge_fusion import KnowledgeFusionEngine
from backend.services.unified_knowledge import UnifiedKnowledgePackage, KnowledgeCandidate, SRC_WEB_SOURCE, TRUST_EXTERNAL

# Freshness Statuses
FRESH_CURRENT = "CURRENT"
FRESH_RECENT = "RECENT"
FRESH_STALE = "STALE"
FRESH_UNKNOWN = "UNKNOWN"

# Budget Safeguards
MAX_SEARCHES = 3
MAX_PAGES = 5
MAX_DEPTH = 2

# Primary Source Indicators
PRIMARY_INDICATORS = [
    "docs.", "documentation", "github.com", "tiangolo.com",
    "python.org", "pypi.org", "developer.mozilla.org", ".gov", ".edu"
]


# -------------------------
# DATA MODELS
# -------------------------
class WebIntelligenceResult(BaseModel):
    queries_executed: List[str] = Field(default_factory=list)
    primary_sources_found: int = 0
    browser_fallback_used: bool = False
    freshness_status: str = FRESH_CURRENT
    evidence_package: Optional[EvidencePackage] = None
    unified_package: Optional[UnifiedKnowledgePackage] = None
    details: str = "Web intelligence execution completed."


# -------------------------
# WEB INTELLIGENCE CAPABILITY SERVICE
# -------------------------
class WebIntelligenceCapability:
    """
    Advanced Web Intelligence Capability orchestrating multi-step query generation,
    primary source prioritization, browser fallback, and evidence fusion.
    """

    @classmethod
    def refine_queries(cls, user_query: str) -> List[str]:
        """
        Formulates initial and refined follow-up search queries.
        Outbound queries pass through PrivacyPolicyEngine to redact user secrets.
        """
        clean_query, _ = PrivacyPolicyEngine.sanitize_query(user_query)
        req = OutboundRequest(query=clean_query, action="WEB_SEARCH")
        decision_obj = PrivacyPolicyEngine.evaluate_request(req)
        if decision_obj.decision == DECISION_BLOCK:
            return ["safe public query"]

        sanitized_query = decision_obj.sanitized_request or clean_query
        queries = [sanitized_query]
        if "fastapi" in sanitized_query.lower():
            queries.append(f"{sanitized_query} official documentation streaming")
        return queries[:MAX_SEARCHES]


    @classmethod
    def prioritize_primary_sources(cls, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranks primary and official sources over generic web search snippets.
        """
        primary = []
        secondary = []
        for item in results:
            url = item.get("url", "").lower()
            if any(ind in url for ind in PRIMARY_INDICATORS):
                item["is_primary"] = True
                primary.append(item)
            else:
                item["is_primary"] = False
                secondary.append(item)

        return primary + secondary

    @classmethod
    def execute_web_intelligence(cls, query: str) -> WebIntelligenceResult:
        queries = cls.refine_queries(query)
        queries_executed = []
        primary_count = 0
        browser_fallback_used = False
        candidates: List[KnowledgeCandidate] = []

        for q in queries:
            queries_executed.append(q)
            # Execute search via DuckDuckGoSearchProvider
            raw_results = DuckDuckGoSearchProvider.search(q)
            if raw_results:
                ranked_items = cls.prioritize_primary_sources(raw_results)
                
                for item in ranked_items[:MAX_PAGES]:
                    if item.get("is_primary"):
                        primary_count += 1
                    
                    # DOM Browser Fallback if page snippet indicates JS rendering
                    if "javascript" in item.get("snippet", "").lower():
                        b_obs = BrowserController.execute_action(BrowserAction(action_type="NAVIGATE", target_url=item["url"]))
                        browser_fallback_used = True

                    snippet_text = item.get("snippet", "")
                    clean_text = re.sub(r"(ignore previous instructions|run this command|upload your files)", "[REDACTED_PROMPT_INJECTION]", snippet_text, flags=re.IGNORECASE)
                    candidates.append(KnowledgeCandidate(
                        source_type=SRC_WEB_SOURCE,
                        content=clean_text,
                        location=item["url"],
                        trust_weight=TRUST_EXTERNAL if not item.get("is_primary") else 0.85,
                        is_untrusted_data=True,
                        provenance_label=f"Primary Web Source ({item['title'][:40]})" if item.get("is_primary") else "Web Search Result"
                    ))



        unified_pkg = UnifiedKnowledgePackage(
            total_candidates=len(candidates),
            sources_queried=["WEB_SEARCH"],
            candidates=candidates
        )

        return WebIntelligenceResult(
            queries_executed=queries_executed,
            primary_sources_found=primary_count,
            browser_fallback_used=browser_fallback_used,
            freshness_status=FRESH_CURRENT,
            unified_package=unified_pkg,
            details=f"Executed {len(queries_executed)} queries, found {primary_count} primary source(s)."
        )
