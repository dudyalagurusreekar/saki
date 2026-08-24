"""
Sprint 4 — Saki Web Pipeline Forensics & Current-Answer Completion Test Suite
Validates:
TEST 1: 'latest FastAPI version' -> web_required = True, temporal_requirement = 'CURRENT'
TEST 2: 'latest FastAPI version' -> Gemini called when configured
TEST 3: 'latest FastAPI version' -> evidence returned when Gemini succeeds
TEST 4: 'latest FastAPI version' -> evidence reaches final model context
TEST 5: 'latest FastAPI version' -> 'no verified records' fallback does NOT run when evidence exists
TEST 6: Gemini failure -> controlled current-information-unavailable response
TEST 7: 'what is FastAPI' -> static knowledge path remains functional
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
    FRESHNESS_CURRENT,
    FRESHNESS_CURRENT_EXTERNAL_FACT,
    FRESHNESS_STABLE,
    ACTION_WEB_SEARCH,
    ACTION_CODING,
    ACTION_LOCAL_REASONING
)
from backend.models.schemas import ChatRequest
from backend.routes.chat import _execute_chat_pipeline
from backend.services.web_controller import WebIntelligenceController


class TestSprint4Forensics:
    """Test suite proving the complete current-information pipeline works end-to-end."""

    def test_01_latest_fastapi_version_web_required(self):
        """TEST 1: 'latest FastAPI version' -> web_required = True and temporal_requirement = 'CURRENT'."""
        query = "latest FastAPI version"
        decision = decide_action(query)
        assert decision.requires_world_access is True
        assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]
        assert decision.temporal_requirement in [FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, "CURRENT", "CURRENT_EXTERNAL_FACT"]
        assert decision.action == ACTION_WEB_SEARCH

    def test_02_latest_fastapi_version_gemini_called(self):
        """TEST 2: 'latest FastAPI version' -> Gemini search provider is invoked with user intent."""
        query = "latest FastAPI version"
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "FastAPI Release Notes",
                    "snippet": "FastAPI version 0.115.0 is current.",
                    "url": "https://fastapi.tiangolo.com/release-notes/",
                    "domain": "fastapi.tiangolo.com",
                    "provider": "Google Search (Gemini Grounded)",
                    "provider_status": "SUCCESS",
                    "grounded_summary": "FastAPI version 0.115.0 is current.",
                    "web_search_queries": ["latest FastAPI version"],
                    "retrieved_at": 1723980000.0
                }
            ]

            req = ChatRequest(message=query, conversation_id="sprint4-test-call")
            p = _execute_chat_pipeline(req)

            mock_search.assert_called_once()
            call_arg = mock_search.call_args[0][0]
            assert "fastapi" in call_arg.lower()
            assert "latest" in call_arg.lower() or "version" in call_arg.lower()

    def test_03_latest_fastapi_version_evidence_returned(self):
        """TEST 3: 'latest FastAPI version' -> EvidencePackage is returned when Gemini succeeds."""
        query = "latest FastAPI version"
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "FastAPI Releases & Documentation",
                    "snippet": "FastAPI 0.115.0 released with Python 3.12 and modern async support.",
                    "url": "https://fastapi.tiangolo.com/release-notes/",
                    "domain": "fastapi.tiangolo.com",
                    "provider": "Google Search (Gemini Grounded)",
                    "provider_status": "SUCCESS",
                    "grounded_summary": "FastAPI 0.115.0 is the latest release.",
                    "web_search_queries": ["latest FastAPI version"],
                    "retrieved_at": 1723980000.0
                }
            ]

            req = ChatRequest(message=query, conversation_id="sprint4-test-ev")
            p = _execute_chat_pipeline(req)

            assert p.evidence_package is not None
            assert p.evidence_package.evidence_status == "SUFFICIENT"
            assert len(p.evidence_items) > 0
            assert p.evidence_items[0].domain == "fastapi.tiangolo.com"
            assert p.evidence_items[0].process_state == "RELEVANT"

    def test_04_latest_fastapi_version_evidence_in_context(self):
        """TEST 4: 'latest FastAPI version' -> Evidence reaches final model prompt context."""
        query = "latest FastAPI version"
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "FastAPI Official Documentation",
                    "snippet": "FastAPI 0.115.0 released on GitHub.",
                    "url": "https://fastapi.tiangolo.com/release-notes/",
                    "domain": "fastapi.tiangolo.com",
                    "provider": "Google Search (Gemini Grounded)",
                    "provider_status": "SUCCESS",
                    "grounded_summary": "FastAPI 0.115.0 is the latest release.",
                    "web_search_queries": ["latest FastAPI version"],
                    "retrieved_at": 1723980000.0
                }
            ]

            req = ChatRequest(message=query, conversation_id="sprint4-test-ctx")
            p = _execute_chat_pipeline(req)

            assert "<external_web_content>" in p.prompt
            assert "fastapi.tiangolo.com" in p.prompt
            assert "0.115.0" in p.prompt
            assert "CURRENT USER QUESTION:" in p.prompt
            assert "WEB EVIDENCE:" in p.prompt

    def test_05_no_verified_records_fallback_does_not_run_when_evidence_exists(self):
        """TEST 5: 'no verified records' refusal directive must NOT be present when evidence exists."""
        query = "latest FastAPI version"
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "FastAPI Official Release",
                    "snippet": "FastAPI 0.115.0 is the latest stable version.",
                    "url": "https://fastapi.tiangolo.com/release-notes/",
                    "domain": "fastapi.tiangolo.com",
                    "provider": "Google Search (Gemini Grounded)",
                    "provider_status": "SUCCESS",
                    "grounded_summary": "FastAPI 0.115.0 is current.",
                    "web_search_queries": ["latest FastAPI version"],
                    "retrieved_at": 1723980000.0
                }
            ]

            req = ChatRequest(message=query, conversation_id="sprint4-test-no-fallback")
            p = _execute_chat_pipeline(req)

            # Refusal directive must NOT be in prompt
            assert "CRITICAL DIRECTIVE: You MUST state that you do not have verified records" not in p.prompt
            assert "NOTE: Web search returned no relevant results" not in p.prompt
            # Factual instruction must be present
            assert "FACTUAL DIRECTIVE:" in p.prompt or "Answer naturally as Saki using the supplied current web evidence" in p.prompt

    def test_06_gemini_failure_controlled_limitation_response(self):
        """TEST 6: When Gemini fails, system enters controlled limitation state without guessing."""
        query = "latest FastAPI version"
        with patch("backend.services.gemini_search.GeminiSearchProvider.search") as mock_search:
            mock_search.return_value = [
                {
                    "title": "",
                    "snippet": "",
                    "url": "",
                    "domain": "",
                    "provider": "gemini",
                    "provider_status": "FAILURE",
                    "error_detail": "HTTP_429",
                    "fallback_from": None
                }
            ]

            req = ChatRequest(message=query, conversation_id="sprint4-test-fail-guard")
            p = _execute_chat_pipeline(req)

            assert p.evidence_items == []
            assert p.evidence_package is None
            assert "CRITICAL DIRECTIVE: You MUST state that you do not have verified records" in p.prompt
            assert "Refuse to guess, speculate, or extrapolate" in p.prompt

    def test_07_what_is_fastapi_static_knowledge_path(self):
        """TEST 7: 'what is FastAPI' uses static/general knowledge path (web_required = False)."""
        query = "what is FastAPI"
        decision = decide_action(query)
        assert decision.requires_world_access is False
        assert decision.freshness_requirement == FRESHNESS_STABLE
        assert decision.temporal_requirement == FRESHNESS_STABLE
        assert decision.action in [ACTION_CODING, ACTION_LOCAL_REASONING]

        req = ChatRequest(message=query, conversation_id="sprint4-test-static")
        p = _execute_chat_pipeline(req)

        assert p.evidence_items == []
        assert p.evidence_package is None
        assert "WEB EVIDENCE:" not in p.prompt
        assert "fastapi.tiangolo.com" not in p.prompt
        assert "CRITICAL DIRECTIVE: You MUST state that you do not have verified records" not in p.prompt
