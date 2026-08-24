"""
Sprint 1 — Web Activation and Duplicate Execution Regression Tests
Validates:
1. Authoritative Web Activation across all 10 standard test queries (Part 11)
2. Zero duplicate search pipeline executions for a single request (Part 12)
3. Observability telemetry recording (Part 10)
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.action_engine import (
    decide_action,
    classify_freshness,
    ACTION_WEB_SEARCH,
    ACTION_LOCAL_REASONING,
    FRESHNESS_CURRENT,
    FRESHNESS_CURRENT_EXTERNAL_FACT,
    FRESHNESS_STABLE
)
from backend.services.web_controller import WebIntelligenceController, WebExecutionResult
from backend.routes.chat import _execute_chat_pipeline
from backend.models.schemas import ChatRequest


class TestSprint1WebActivation:
    """Test suite verifying Web Activation accuracy and Date Awareness (August 2026)."""

    def test_01_special_food_in_vijayawada(self):
        """TEST 1: Local culinary query must require web access."""
        query = "special food in Vijayawada"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH

    def test_02_kambadur_heritage_monuments(self):
        """TEST 2: Obscure regional heritage query must require web access."""
        query = "Kambadur heritage monuments"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH

    def test_03_movies_2026(self):
        """TEST 3: Current-year media recommendation query must require web access."""
        query = "Good movies in 2026"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, "CURRENT", "CURRENT_EXTERNAL_FACT"]

    def test_04_what_is_fastapi(self):
        """TEST 4: Static conceptual question must NOT require web access."""
        query = "What is FastAPI?"
        decision = decide_action(query)
        assert decision.requires_world_access is False
        assert decision.action in [ACTION_LOCAL_REASONING, "CODING"]
        assert decision.freshness_requirement == FRESHNESS_STABLE

    def test_05_latest_fastapi_version(self):
        """TEST 5: Latest software release version must require web access."""
        query = "What is the latest FastAPI version?"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]

    def test_06_how_are_you_saki(self):
        """TEST 6: Conversational casual banter must NOT require web access."""
        query = "How are you Saki?"
        decision = decide_action(query)
        assert decision.requires_world_access is False
        assert decision.action == ACTION_LOCAL_REASONING
        assert decision.freshness_requirement == FRESHNESS_STABLE

    def test_07_best_places_to_visit_vijayawada(self):
        """TEST 7: Local travel recommendation for the weekend must require web access."""
        query = "Best places to visit in Vijayawada this weekend"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH

    def test_08_who_invented_python(self):
        """TEST 8: Static historical entity knowledge must NOT require web access."""
        query = "Who invented Python?"
        decision = decide_action(query)
        assert decision.requires_world_access is False
        assert decision.freshness_requirement == FRESHNESS_STABLE

    def test_09_what_happened_in_ai_today(self):
        """TEST 9: Time-sensitive today news query must require web access."""
        query = "What happened in AI today?"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH
        assert decision.freshness_requirement == FRESHNESS_CURRENT

    def test_10_obscure_local_temple(self):
        """TEST 10: Obscure local temple query must require web access."""
        query = "Tell me about an obscure local temple in Andhra Pradesh"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.action == ACTION_WEB_SEARCH


class TestSprint1DuplicateSearchPrevention:
    """Test suite proving exactly ONE Saki-level web search pipeline executes per request."""

    @patch("backend.services.gemini_search.GeminiSearchProvider.search")
    def test_duplicate_search_elimination_for_chat_pipeline(self, mock_gemini_search):
        """
        Part 12: Verify that for 'special food in Vijayawada',
        GeminiSearchProvider.search is called exactly ONCE at the pipeline level,
        and not independently repeated by UnifiedKnowledgeEngine or WebIntelligenceCapability.
        """
        # Mock Gemini search response
        mock_gemini_search.return_value = [
            {
                "title": "Famous Foods of Vijayawada",
                "snippet": "Punayalu, Mirchi Bajji, and Gongura Mutton are signature dishes of Vijayawada.",
                "url": "https://ap.gov.in/culinary-heritage",
                "domain": "ap.gov.in",
                "provider": "Google Search (Gemini Grounded)",
                "provider_status": "SUCCESS",
                "grounded_summary": "Punayalu, Mirchi Bajji, and Gongura Mutton are signature dishes of Vijayawada.",
                "web_search_queries": ["special food in Vijayawada"],
                "retrieved_at": 1723980000.0
            }
        ]

        req = ChatRequest(
            message="special food in Vijayawada",
            conversation_id="test-sprint1-dedup"
        )

        pipeline_result = _execute_chat_pipeline(req)

        # 1. Authoritative Web Execution must have occurred
        assert pipeline_result.evidence_items is not None
        assert len(pipeline_result.evidence_items) > 0
        assert pipeline_result.evidence_items[0].title == "Famous Foods of Vijayawada"

        # 2. Exactly ONE search call must have been issued by the controller
        assert mock_gemini_search.call_count == 1

        # 3. Web Intelligence telemetry must be populated from the single execution
        assert pipeline_result.web_intel_res is not None
        assert pipeline_result.web_intel_res.primary_sources_found >= 1

        # 4. Diagnostic tracer must confirm DUPLICATE_PIPELINE is False
        last_trace = WebIntelligenceController._last_diagnostic_trace
        assert last_trace is not None
        assert last_trace.get("DUPLICATE_PIPELINE") is False
        assert last_trace.get("PROVIDER_CALLS") == 1
