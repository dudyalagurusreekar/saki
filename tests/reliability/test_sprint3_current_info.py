"""
Sprint 3 — Saki Current Information & Web-to-Answer Pipeline Test Suite
Validates:
1. Current/temporal intent and software-version triggers (Tests 1-5)
2. Temporal year reasoning: 2025 (past), 2026 (current), 2027 (future) (Tests 6-8)
3. Controlled failure on Gemini error/empty without hallucination (Tests 9-10)
4. End-to-end evidence propagation from Gemini to final model answer context (Test 11)
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
from backend.models.schemas import ChatRequest
from backend.routes.chat import _execute_chat_pipeline
from backend.services.web_controller import WebIntelligenceController


class TestSprint3CurrentInformation:
    """Test suite verifying end-to-end current information routing and evidence delivery."""

    def test_01_what_current_fastapi_version(self):
        """TEST 1: 'what current fastapi version' requires web, executes pipeline, delivers evidence to context."""
        query = "what current fastapi version"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]

        # Mock Gemini search returning current version evidence
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "FastAPI Release Notes & Versions",
                    "snippet": "FastAPI 0.115.0 was released with modern Python 3.12 support and Pydantic v2 integration.",
                    "url": "https://fastapi.tiangolo.com/release-notes/",
                    "domain": "fastapi.tiangolo.com",
                    "provider": "Google Search (Gemini Grounded)",
                    "provider_status": "SUCCESS",
                    "grounded_summary": "FastAPI 0.115.0 is the current version released in 2026.",
                    "web_search_queries": ["what current fastapi version"],
                    "retrieved_at": 1723980000.0
                }
            ]

            req = ChatRequest(message=query, conversation_id="test-sprint3-fastapi-curr")
            p = _execute_chat_pipeline(req)

            # 1. Pipeline result checks
            assert p.evidence_items is not None
            assert len(p.evidence_items) > 0
            assert p.evidence_package is not None
            assert p.evidence_package.evidence_status == "SUFFICIENT"

            # 2. Evidence must reach final answer model prompt context
            assert "<external_web_content>" in p.prompt
            assert "fastapi.tiangolo.com" in p.prompt
            assert "0.115.0" in p.prompt
            assert "CURRENT USER QUESTION:" in p.prompt

    def test_02_what_is_latest_fastapi_version(self):
        """TEST 2: 'what is the latest fastapi version' requires web."""
        decision = decide_action("what is the latest fastapi version")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]

    def test_03_what_is_fastapi_static(self):
        """TEST 3: 'what is FastAPI?' is static knowledge and does not require web."""
        decision = decide_action("what is FastAPI?")
        assert decision.requires_world_access is False
        assert decision.freshness_requirement == FRESHNESS_STABLE

    def test_04_latest_python_version(self):
        """TEST 4: 'latest Python version' requires web."""
        decision = decide_action("latest Python version")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]

    def test_05_what_happened_in_ai_today(self):
        """TEST 5: 'what happened in AI today' requires web."""
        decision = decide_action("what happened in AI today")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]

    def test_06_good_movies_in_2026(self):
        """TEST 6: 'good movies in 2026' is recognized as current year (2026)."""
        decision = decide_action("good movies in 2026")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement == FRESHNESS_CURRENT

    def test_07_movies_in_2025(self):
        """TEST 7: 'movies in 2025' is recognized as past historical knowledge."""
        decision = decide_action("movies in 2025")
        assert decision.requires_world_access is False
        assert decision.freshness_requirement == FRESHNESS_STABLE

    def test_08_movies_in_2027(self):
        """TEST 8: 'movies in 2027' is recognized as future/upcoming information."""
        decision = decide_action("movies in 2027")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement == FRESHNESS_CURRENT

    def test_09_gemini_failure_no_hallucination(self):
        """TEST 9: When Gemini fails, pipeline injects strict refusal without hallucination."""
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [{
                "title": "",
                "snippet": "",
                "url": "",
                "domain": "",
                "provider": "gemini",
                "provider_status": "FAILURE",
                "error_detail": "HTTP_503"
            }]

            req = ChatRequest(message="what current fastapi version", conversation_id="test-sprint3-fail")
            p = _execute_chat_pipeline(req)

            assert p.evidence_items == []
            assert p.evidence_package is None
            assert "CRITICAL DIRECTIVE: You MUST state that you do not have verified records" in p.prompt
            assert "Refuse to guess, speculate, or extrapolate" in p.prompt

    def test_10_empty_gemini_results(self):
        """TEST 10: When Gemini returns empty results, pipeline enters controlled insufficient state."""
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = []

            req = ChatRequest(message="what current fastapi version", conversation_id="test-sprint3-empty")
            p = _execute_chat_pipeline(req)

            assert p.evidence_items == []
            assert p.evidence_package is None
            assert "CRITICAL DIRECTIVE: You MUST state that you do not have verified records" in p.prompt

    def test_11_evidence_actually_present_in_final_answer_context(self):
        """TEST 11: Verified evidence from Gemini is fully preserved in the final model prompt context."""
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "Python 3.12 Official Release",
                    "snippet": "Python 3.12.5 is the latest bugfix release available on python.org.",
                    "url": "https://www.python.org/downloads/release/python-3125/",
                    "domain": "python.org",
                    "provider": "Google Search (Gemini Grounded)",
                    "provider_status": "SUCCESS",
                    "grounded_summary": "Python 3.12.5 is the current stable release.",
                    "web_search_queries": ["latest Python version"],
                    "retrieved_at": 1723980000.0
                }
            ]

            req = ChatRequest(message="latest Python version", conversation_id="test-sprint3-py-evidence")
            p = _execute_chat_pipeline(req)

            assert "<external_web_content>" in p.prompt
            assert "Source: Python 3.12 Official Release" in p.prompt
            assert "https://www.python.org/downloads/release/python-3125" in p.prompt
            assert "Python 3.12.5" in p.prompt
            assert "FACTUAL DIRECTIVE:" in p.prompt
