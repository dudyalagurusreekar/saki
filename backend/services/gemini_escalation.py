"""
Saki Last-Resort Gemini Answer Escalation Engine (Sprint Final)
Provides a hardened final fallback mechanism for queries where Saki's internal pipeline
cannot produce a valid answer. Escalate directly to Gemini and return the answer directly.
"""

import re
import time
import httpx
from typing import Tuple, Optional, Any, Dict

from backend.core.config import settings
from backend.services.gemini_search import GEMINI_API_ENDPOINT


CANNED_REFUSAL_PATTERNS = [
    r"\bi (?:don't|do not) have (?:verified|active|access|records)\b",
    r"\bi'm sorry, but i (?:don't|do not) have\b",
    r"\bi cannot confirm\b",
    r"\bi am unable to (?:confirm|find|verify)\b",
    r"\bcould not retrieve enough information\b",
    r"\bno relevant results or insufficient verified information\b",
    r"\bi don't have the updated info\b",
    r"\bi can't find the latest version on record\b",
    r"\bcan't confirm specifics without verified records\b",
    r"\bi don't have verified records or active web search results\b"
]

INABILITY_AND_DEFLECTION_PATTERNS = [
    # Future / Time deflection
    r"\b(?:can't|cannot|unable to) (?:tap into the future|look into the future|predict the future|check the latest|find the latest|get the latest|confirm the latest)\b",
    r"\b(?:reminisce on|look back at|instead.*reminisce|older movies|classics instead|past few years for inspiration|classics that have stood the test)\b",
    r"\b(?:don't|do not) have (?:the crystal ball|a crystal ball|crystal ball)\b",
    # Inability / lack of current info
    r"\b(?:don't|do not) have (?:the latest|current|updated|real-time|verified|access to|records|info)\b",
    r"\b(?:wish i could tell you|can't find specific info|behind on that front|don't have the inside scoop)\b",
    r"\b(?:make sure to check (?:the latest|official)|check the latest info from|why not ask someone)\b",
    r"\b(?:my knowledge only goes up to|cutoff date|knowledge cutoff)\b",
    r"\b(?:can't verify specifics without|can't confirm specifics without)\b",
    r"\b(?:i don't know|not sure|unable to provide|cannot provide)\b"
]

# Version claim detection — catches "version X.Y", "Python 3.11", version numbers like "3.11", etc.
VERSION_CLAIM_PATTERNS = [
    r"\b\d+\.\d+(?:\.\d+)*\b",
    r"\b(?:version|v\d+|release|build)\b",
]


class GeminiEscalationEngine:
    """Last-resort escalation coordinator for unanswered queries."""

    @classmethod
    def is_canned_refusal(cls, text: str) -> bool:
        """Determines if the response is an internal refusal/limitation message."""
        if not text or len(text.strip()) < 10:
            return True
        text_lower = text.lower()
        return any(re.search(pat, text_lower) for pat in CANNED_REFUSAL_PATTERNS)

    @classmethod
    def validate_temporal_consistency(
        cls,
        draft_text: str,
        user_query: str = "",
        runtime_year: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validates generated text against current runtime date to catch stale/future hallucinations:
        - Claims that past years (e.g. 2023, 2024) are the current year.
        - Claims that the current runtime year (e.g. 2026) is in the future or hasn't happened yet.
        """
        from datetime import datetime
        if runtime_year is None:
            runtime_year = datetime.now().year

        text_lower = (draft_text or "").lower()

        # 1. Past year claimed as present
        for past_yr in range(2015, runtime_year):
            past_patterns = [
                rf"\bthe year(?:'s| is) (?:still )?{past_yr}\b",
                rf"\bcurrently in {past_yr}\b",
                rf"\bthe present and the year(?:'s| is) (?:still )?{past_yr}\b",
                rf"\bsince (?:it is|we are in) {past_yr}\b",
                rf"\bpresent and the year(?:'s| is) (?:still )?{past_yr}\b"
            ]
            for pat in past_patterns:
                if re.search(pat, text_lower):
                    return False, f"TEMPORAL_INCONSISTENCY: claimed current year is {past_yr}"

        # 2. Current runtime year claimed as future
        future_patterns = [
            rf"\b{runtime_year} is (?:still )?(?:in the )?future\b",
            rf"\b{runtime_year} (?:has not|hasn't) happened yet\b",
            rf"\bmovies in {runtime_year} yet\b",
            rf"\bcrystal ball for (?:movies in )?{runtime_year}\b",
            rf"\bcan't wait to see unfold.*{runtime_year}\b",
            rf"\blooking ahead to {runtime_year}\b",
            rf"\b{runtime_year} (?:cannot be known|is a future)\b",
            r"\bcan't tap into the future\b"
        ]
        for pat in future_patterns:
            if re.search(pat, text_lower):
                return False, f"TEMPORAL_INCONSISTENCY: claimed runtime year {runtime_year} is in the future"

        return True, "TEMPORALLY_CONSISTENT"

    @classmethod
    def is_invalid_current_draft(
        cls,
        draft_text: str,
        user_query: str = "",
        is_current_query: bool = False,
        runtime_year: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a generated draft is invalid for a query requiring current information:
        1. Temporal inconsistencies (claims 2026 is future or 2023 is present).
        2. Deflections and admissions of inability on current-information questions.
        """
        # 1. Check general temporal consistency
        is_temp_valid, temp_reason = cls.validate_temporal_consistency(draft_text, user_query, runtime_year)
        if not is_temp_valid:
            return True, temp_reason

        # 2. Check if draft deflects or admits inability when current information is required
        if is_current_query:
            text_lower = (draft_text or "").lower()
            for pat in INABILITY_AND_DEFLECTION_PATTERNS:
                if re.search(pat, text_lower):
                    return True, "TEMPORAL_INSUFFICIENCY: draft admits inability or deflects on current information"

        return False, "VALID"

    @classmethod
    def is_stale_current_fact_answer(
        cls,
        draft_text: str,
        user_query: str,
        evidence_items: list = None,
        evidence_package: Any = None,
        action_decision: Any = None
    ) -> Tuple[bool, str]:
        """
        Detects when a response contains a version/release claim but has NO supporting
        external evidence. This is the core gate for CURRENT_EXTERNAL_FACT queries.
        
        Returns (is_stale, reason).
        """
        from backend.services.action_engine import (
            is_current_external_fact_query,
            FRESHNESS_CURRENT_EXTERNAL_FACT
        )

        # Only applies to current-external-fact queries
        freshness = getattr(action_decision, "freshness_requirement", "STABLE") if action_decision else "STABLE"
        query_intent = getattr(action_decision, "query_intent", "") if action_decision else ""
        
        is_cef = (
            freshness == FRESHNESS_CURRENT_EXTERNAL_FACT or
            query_intent == "current_external_fact" or
            is_current_external_fact_query(user_query)
        )

        if not is_cef:
            return False, "NOT_CURRENT_EXTERNAL_FACT"

        # Check if the response contains a version claim
        text_lower = (draft_text or "").lower()
        has_version_claim = any(re.search(pat, text_lower) for pat in VERSION_CLAIM_PATTERNS)

        if not has_version_claim:
            # Response doesn't make a version claim — might be a refusal (caught elsewhere)
            return False, "NO_VERSION_CLAIM_IN_RESPONSE"

        # Check if we have USABLE external evidence
        has_evidence = False
        
        if evidence_items and len(evidence_items) > 0:
            has_evidence = True
        
        if evidence_package and hasattr(evidence_package, "evidence_status"):
            if evidence_package.evidence_status == "INSUFFICIENT":
                has_evidence = False

        if has_evidence:
            return False, "HAS_SUPPORTING_EVIDENCE"

        # Version claim + no evidence = STALE MODEL ANSWER
        return True, "STALE_VERSION_CLAIM: Response contains version claim but has no supporting external evidence"

    @classmethod
    def should_escalate(
        cls,
        user_query: str,
        final_response: str,
        eval_result: Optional[Any] = None,
        evidence_package: Optional[Any] = None,
        action_decision: Optional[Any] = None,
        already_attempted: bool = False,
        evidence_items: Optional[list] = None
    ) -> Tuple[bool, str]:
        """
        Determines whether the request must be escalated to Gemini.
        Escalates ONLY when Saki attempted normal processing and genuinely cannot answer.
        """
        if already_attempted:
            return False, "ALREADY_ESCALATED"

        # 1. Check if Saki produced a canned refusal
        is_refusal = cls.is_canned_refusal(final_response)
        if is_refusal:
            return True, "SAKI_CANNED_REFUSAL"

        # 2. Check general temporal consistency (past claimed as present or current claimed as future)
        is_temp_valid, temp_reason = cls.validate_temporal_consistency(final_response, user_query)
        if not is_temp_valid:
            return True, "TEMPORAL_INCONSISTENCY"

        # Determine if query requires current/external information
        requires_web = bool(action_decision and getattr(action_decision, "requires_world_access", False))
        freshness = getattr(action_decision, "freshness_requirement", "STABLE") if action_decision else "STABLE"
        is_current_query = (
            requires_web or 
            (freshness in ["CURRENT", "CURRENT_EXTERNAL_FACT", "LIVE", "USER_EXPLICIT_SEARCH"]) or 
            any(k in user_query.lower() for k in ["latest", "current", "2026", "today", "now", "newest", "recent", "this year", "best movies", "movies in", "watch in 2026"])
        )

        # 3. CURRENT_EXTERNAL_FACT GATE: Reject stale version claims without evidence
        is_stale, stale_reason = cls.is_stale_current_fact_answer(
            draft_text=final_response,
            user_query=user_query,
            evidence_items=evidence_items or [],
            evidence_package=evidence_package,
            action_decision=action_decision
        )
        if is_stale:
            return True, f"STALE_CURRENT_FACT: {stale_reason}"

        # 4. Check if draft deflects or admits inability on current-information query
        is_invalid, invalid_reason = cls.is_invalid_current_draft(
            draft_text=final_response,
            user_query=user_query,
            is_current_query=is_current_query
        )
        if is_invalid:
            return True, "INVALID_CURRENT_DRAFT"

        # 5. Check grounding assessment status
        grounding_status = ""
        if eval_result and hasattr(eval_result, "grounding_assessment") and eval_result.grounding_assessment:
            grounding_status = eval_result.grounding_assessment.grounding_status

        # 6. Check evidence package status
        ev_status = ""
        if evidence_package and hasattr(evidence_package, "evidence_status"):
            ev_status = evidence_package.evidence_status

        # Condition B: Web-required query with insufficient or unsupported grounding
        if requires_web and grounding_status in ["INSUFFICIENT_EVIDENCE", "UNSUPPORTED", "TEMPORAL_INCONSISTENCY"]:
            return True, f"GROUNDING_{grounding_status}"

        # Condition C: Evidence package was completely insufficient on factual query
        if requires_web and ev_status == "INSUFFICIENT" and is_refusal:
            return True, "INSUFFICIENT_EVIDENCE_PACKAGE"

        # Condition D: CURRENT_EXTERNAL_FACT with no evidence at all (even if no version claim — catch-all)
        from backend.services.action_engine import is_current_external_fact_query, FRESHNESS_CURRENT_EXTERNAL_FACT
        is_cef = (
            freshness == FRESHNESS_CURRENT_EXTERNAL_FACT or
            getattr(action_decision, "query_intent", "") == "current_external_fact" if action_decision else False or
            is_current_external_fact_query(user_query)
        )
        if is_cef and ev_status == "INSUFFICIENT":
            return True, "CURRENT_EXTERNAL_FACT_NO_EVIDENCE"

        return False, "SAKI_ANSWERED_NORMALLY"

    @classmethod
    def escalate_to_gemini(
        cls,
        user_query: str,
        timeout: float = 15.0
    ) -> Tuple[Optional[str], str, float]:
        """
        Dispatches original user query directly to Gemini with Google Search tool.
        Returns (gemini_response_text, status, latency_ms).
        """
        t0 = time.time()
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_api_key_here":
            return None, "GEMINI_NOT_CONFIGURED", round((time.time() - t0) * 1000, 2)

        model_name = getattr(settings, "GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
        url = f"{GEMINI_API_ENDPOINT.format(model=model_name)}?key={api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_query}]
                }
            ],
            "tools": [
                {"google_search": {}}
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1024
            }
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
            latency = round((time.time() - t0) * 1000, 2)

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        gemini_text = parts[0]["text"].strip()
                        if len(gemini_text) > 10:
                            # Validate Gemini's response for temporal consistency (Part 12)
                            is_valid, reason = cls.validate_temporal_consistency(gemini_text, user_query)
                            if not is_valid:
                                return None, f"GEMINI_REJECTED_{reason}", latency
                            return gemini_text, "SUCCESS", latency

                return None, "EMPTY_GEMINI_RESPONSE", latency
            else:
                return None, f"HTTP_{resp.status_code}", latency

        except httpx.TimeoutException:
            latency = round((time.time() - t0) * 1000, 2)
            return None, "GEMINI_TIMEOUT", latency
        except Exception as e:
            latency = round((time.time() - t0) * 1000, 2)
            return None, f"EXCEPTION_{type(e).__name__}", latency
