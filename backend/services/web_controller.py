"""
Saki Authoritative Web Intelligence Controller (WebIntelligenceController)
Provides the SINGLE, authoritative entry point for all external web search,
fetching, evidence synthesis, and grounding across Saki's entire runtime lifecycle.
Guarantees:
1. Exactly ONE Saki-level web execution per request.
2. Explicit provider transparency (Gemini Google Grounding / WebFetcher).
3. Zero silent fallback to fabricated or synthetic evidence.
4. Comprehensive observability telemetry without leaking prompt internals.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.privacy import (
    PrivacyPolicyEngine,
    OutboundRequest,
    DECISION_BLOCK,
    DECISION_REQUIRE_CONFIRMATION,
    PrivacyAuditLogger
)
from backend.services.action_engine import (
    ActionDecision,
    ACTION_WEB_SEARCH,
    ACTION_WEB_FETCH,
    ACTION_WEB_RESEARCH
)
from backend.services.evidence_engine import (
    EvidenceIntelligenceEngine,
    EvidencePackage,
    EvidenceItem
)
from backend.services.world_access_manager import (
    EvidenceEngine,
    WebFetcher,
    DiagnosticTracer
)
from backend.services.gemini_search import GeminiSearchProvider


# -------------------------
# WEB EXECUTION RESULT MODEL
# -------------------------
class WebExecutionResult(BaseModel):
    web_required: bool = Field(default=False)
    web_activation_reason: str = Field(default="")
    temporal_intent: str = Field(default="STABLE")
    controller_name: str = Field(default="WebIntelligenceController")
    provider: str = Field(default="gemini")
    provider_status: str = Field(default="SUCCESS", description="SUCCESS, FAILURE, BLOCKED, SKIPPED")
    provider_call_count: int = Field(default=0)
    queries_executed: List[str] = Field(default_factory=list)
    result_count: int = Field(default=0)
    evidence_count: int = Field(default=0)
    evidence_passed_to_model: bool = Field(default=False)
    is_duplicate: bool = Field(default=False, description="Guaranteed False under unified controller")
    evidence_package: Optional[EvidencePackage] = None
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    grounded_prompt_block: str = Field(default="")
    final_answer: Optional[str] = Field(default=None)
    details: str = Field(default="")


# -------------------------
# AUTHORITATIVE CONTROLLER
# -------------------------
class WebIntelligenceController:
    """
    Authoritative single-brain controller for Saki's external web grounding.
    Enforces one request -> one decision -> one execution -> one structured result.
    """
    _last_execution_result: Optional[WebExecutionResult] = None
    _last_diagnostic_trace: Optional[Dict[str, Any]] = None

    @classmethod
    def execute(
        cls,
        query: str,
        action_decision: ActionDecision,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> WebExecutionResult:
        """
        Executes external web intelligence if required by action_decision.
        """
        # 1. Check if web is required
        if not action_decision or not action_decision.requires_world_access:
            return WebExecutionResult(
                web_required=False,
                web_activation_reason=action_decision.reason if action_decision else "No world access required",
                provider_status="SKIPPED",
                details="Web access not required for this request."
            )

        user_query = (query or "").strip()
        action_type = action_decision.action

        # 2. Privacy Policy Gate
        outbound_req = OutboundRequest(
            action=action_type,
            destination="PUBLIC_SEARCH" if action_type in [ACTION_WEB_SEARCH, ACTION_WEB_RESEARCH] else "PUBLIC_WEBPAGE",
            query=user_query,
            requested_capability=action_type,
            privacy_mode=settings.PRIVACY_MODE
        )
        privacy_decision = PrivacyPolicyEngine.evaluate_request(outbound_req)
        PrivacyAuditLogger.log_decision(privacy_decision, action=action_type)

        if privacy_decision.decision in [DECISION_BLOCK, DECISION_REQUIRE_CONFIRMATION]:
            res = WebExecutionResult(
                web_required=True,
                web_activation_reason=action_decision.reason,
                provider="PrivacyPolicyEngine",
                provider_status="BLOCKED",
                provider_call_count=0,
                queries_executed=[],
                result_count=0,
                is_duplicate=False,
                details=f"Web execution blocked by privacy policy: {privacy_decision.reason}"
            )
            cls._last_execution_result = res
            return res

        sanitized_query = privacy_decision.sanitized_request or user_query
        provider_calls = 0
        raw_items: List[Dict[str, Any]] = []
        evidence_items: List[EvidenceItem] = []
        provider_name = "Google Search (Gemini Grounded)"
        provider_status = "SUCCESS"

        # Use optimized search query if available from QueryUnderstanding
        qu = getattr(action_decision, "query_understanding", None)
        search_query = (qu.search_query_optimized if qu and qu.search_query_optimized else sanitized_query)
        queries_executed: List[str] = [search_query]

        # 3. Authoritative Dispatch Based on Action Type
        if action_type == ACTION_WEB_FETCH:
            url_match = re.search(r"https?://[^\s]+", sanitized_query) or re.search(r"https?://[^\s]+", user_query)
            if url_match:
                target_url = url_match.group(0)
                provider_calls += 1
                success, title, text = WebFetcher.fetch_url(target_url)
                if success:
                    item = EvidenceEngine.normalize_fetch_result(target_url, title, text)
                    evidence_items.append(item)
                    raw_items.append({
                        "title": title,
                        "snippet": text,
                        "url": target_url,
                        "domain": item.domain,
                        "provider": "WebFetcher",
                        "provider_status": "SUCCESS"
                    })
                    provider_name = "WebFetcher"
                else:
                    provider_status = "FAILURE"
                    provider_name = "WebFetcher"
            else:
                # Fallback to search if no URL found
                provider_calls += 1
                search_results = GeminiSearchProvider.search(search_query, max_results=3)
                raw_items.extend(search_results)

        elif action_type in [ACTION_WEB_SEARCH, ACTION_WEB_RESEARCH]:
            max_r = 5 if action_type == ACTION_WEB_RESEARCH else 4
            provider_calls += 1
            search_results = GeminiSearchProvider.search(search_query, max_results=max_r)
            raw_items.extend(search_results)

        # 4. Check Provider Failure
        # If search provider returned failure stub or nothing
        has_failure_stub = any(item.get("provider_status") == "FAILURE" for item in raw_items)
        if has_failure_stub or not raw_items:
            provider_status = "FAILURE"
            if raw_items:
                provider_name = raw_items[0].get("provider", provider_name)

        # Normalize raw results into evidence items
        if raw_items and provider_status == "SUCCESS":
            evidence_items = EvidenceEngine.normalize_search_results(sanitized_query, raw_items)
            provider_name = raw_items[0].get("provider", provider_name)

        # 5. Synthesize Structured EvidencePackage
        package: Optional[EvidencePackage] = None
        grounded_block = ""
        final_evidence_items: List[EvidenceItem] = []

        if raw_items and provider_status == "SUCCESS":
            is_verification = (action_decision.query_intent == "verification")
            package = EvidenceIntelligenceEngine.process_and_synthesize(
                query=user_query,
                raw_items=raw_items,
                freshness_requirement=action_decision.freshness_requirement,
                is_verification_mode=is_verification
            )
            grounded_block = EvidenceIntelligenceEngine.format_grounded_prompt_block(package)
            final_evidence_items = package.evidence_items if package else []
        elif provider_status == "FAILURE":
            # Fail closed: No synthetic evidence
            package = None
            final_evidence_items = []
            grounded_block = ""

        # 6. Diagnostic Logging (Part 17 Relevance Telemetry)
        passed_to_model = (len(final_evidence_items) > 0 and len(grounded_block) > 0)
        relevance_trace = [ev.provenance.get("relevance_diagnostics", {}) for ev in final_evidence_items if ev.provenance.get("relevance_diagnostics")]
        
        tracer = DiagnosticTracer.build_trace(
            user_query=user_query,
            action=action_type,
            sanitized_query=sanitized_query,
            package=package,
            final_prompt_context=grounded_block
        )
        tracer["QUERY"] = user_query
        tracer["query"] = user_query
        tracer["normalized_query"] = sanitized_query
        tracer["entity"] = getattr(qu, "primary_entity", None) if qu else None
        tracer["topic"] = getattr(qu, "topic", None) if qu else None
        tracer["intent"] = getattr(qu, "intent", None) if qu else None
        tracer["location"] = getattr(qu, "location", None) if qu else None
        tracer["TEMPORAL_INTENT"] = action_decision.freshness_requirement
        tracer["temporal_intent"] = action_decision.freshness_requirement
        tracer["WEB_REQUIRED"] = True
        tracer["web_required"] = True
        tracer["ACTION"] = action_type
        tracer["SEARCH_PROVIDER"] = provider_name
        tracer["provider"] = provider_name
        tracer["provider_called"] = provider_calls > 0
        tracer["PROVIDER_STATUS"] = provider_status
        tracer["provider_status"] = provider_status
        tracer["provider_query"] = queries_executed[0] if queries_executed else sanitized_query
        tracer["QUERIES_EXECUTED"] = queries_executed
        tracer["RESULT_COUNT"] = len(raw_items)
        tracer["result_count"] = len(raw_items)
        tracer["grounding_count"] = len(raw_items)
        tracer["EVIDENCE_COUNT"] = len(final_evidence_items)
        tracer["evidence_count"] = len(final_evidence_items)
        tracer["EVIDENCE_PASSED_TO_MODEL"] = passed_to_model
        tracer["evidence_passed_to_model"] = passed_to_model
        tracer["relevance_evaluations"] = relevance_trace
        tracer["PROVIDER_CALLS"] = provider_calls
        tracer["DUPLICATE_PIPELINE"] = False
        cls._last_diagnostic_trace = tracer

        result = WebExecutionResult(
            web_required=True,
            web_activation_reason=action_decision.reason,
            temporal_intent=action_decision.freshness_requirement,
            controller_name="WebIntelligenceController",
            provider=provider_name,
            provider_status=provider_status,
            provider_call_count=provider_calls,
            queries_executed=queries_executed,
            result_count=len(raw_items),
            evidence_count=len(final_evidence_items),
            evidence_passed_to_model=passed_to_model,
            is_duplicate=False,
            evidence_package=package,
            evidence_items=final_evidence_items,
            grounded_prompt_block=grounded_block,
            details=f"Authoritative web execution completed via {provider_name} with status {provider_status} ({len(final_evidence_items)} sources retrieved)."
        )
        cls._last_execution_result = result
        return result

    @classmethod
    def get_last_diagnostic_trace(cls) -> Dict[str, Any]:
        return cls._last_diagnostic_trace or {}
