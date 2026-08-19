"""
Final Patch Automated Test Suite: Current-Date Sanity & Last-Resort Gemini Escalation
Covers Tests 1-11 required by Final Patch specifications.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.action_engine import (
    classify_freshness,
    parse_query_understanding,
    decide_action,
    FRESHNESS_CURRENT,
    FRESHNESS_STABLE,
    get_runtime_year
)
from backend.services.gemini_escalation import GeminiEscalationEngine
from backend.routes.chat import ChatRequest, chat


class TestFinalPatchTemporalAndEscalation:
    """Automated tests for dynamic runtime date, temporal consistency, and last-resort escalation."""

    def test_01_current_year_query_movies_in_2026(self):
        """TEST 1: Runtime 2026, Query 'movies in 2026' -> CURRENT_YEAR_QUERY (FRESHNESS_CURRENT)."""
        runtime_year = 2026
        freshness = classify_freshness("movies in 2026", runtime_year=runtime_year)
        assert freshness == FRESHNESS_CURRENT

        qu = parse_query_understanding("movies in 2026")
        assert qu.temporal_requirement == FRESHNESS_CURRENT

    def test_02_historical_year_query_movies_in_2025(self):
        """TEST 2: Runtime 2026, Query 'movies in 2025' -> HISTORICAL_YEAR_QUERY (FRESHNESS_STABLE)."""
        runtime_year = 2026
        freshness = classify_freshness("movies in 2025", runtime_year=runtime_year)
        assert freshness == FRESHNESS_STABLE

    def test_03_future_year_query_movies_in_2027(self):
        """TEST 3: Runtime 2026, Query 'movies in 2027' -> FUTURE_YEAR_QUERY (FRESHNESS_CURRENT)."""
        runtime_year = 2026
        freshness = classify_freshness("movies in 2027", runtime_year=runtime_year)
        assert freshness == FRESHNESS_CURRENT

    def test_04_current_information_required_latest_fastapi_version(self):
        """TEST 4: Runtime 2026, Query 'latest FastAPI version' -> CURRENT_INFORMATION_REQUIRED."""
        runtime_year = 2026
        freshness = classify_freshness("latest FastAPI version", runtime_year=runtime_year)
        assert freshness == FRESHNESS_CURRENT

        decision = decide_action("latest FastAPI version")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement == FRESHNESS_CURRENT

    def test_05_temporal_inconsistency_claimed_2026_is_future(self):
        """TEST 5: Runtime 2026, Draft '2026 is in the future.' -> TEMPORAL_INCONSISTENCY."""
        draft = "Hey, that's a future I can't wait to see unfold! But since 2026 is in the future, I don't have movie records yet."
        is_valid, reason = GeminiEscalationEngine.validate_temporal_consistency(
            draft_text=draft,
            user_query="best movies available in 2026",
            runtime_year=2026
        )

        assert is_valid is False
        assert "TEMPORAL_INCONSISTENCY" in reason

    def test_06_temporal_inconsistency_claimed_current_year_is_2023(self):
        """TEST 6: Runtime 2026, Draft 'the current year is 2023.' -> TEMPORAL_INCONSISTENCY."""
        draft = "Since I'm currently in the present and the year's still 2023, I don't have the crystal ball for movies in 2026 yet."
        is_valid, reason = GeminiEscalationEngine.validate_temporal_consistency(
            draft_text=draft,
            user_query="best movies available in 2026",
            runtime_year=2026
        )

        assert is_valid is False
        assert "TEMPORAL_INCONSISTENCY" in reason

    def test_07_no_unnecessary_escalation_what_is_fastapi(self):
        """TEST 7: Query 'what is FastAPI?' -> NO_UNNECESSARY_ESCALATION."""
        user_query = "what is FastAPI"
        final_response = "FastAPI is a modern, high-performance web framework for building APIs with Python."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            action_decision=decision
        )

        assert should_esc is False
        assert reason == "SAKI_ANSWERED_NORMALLY"

    def test_08_saki_cannot_answer_current_query_escalates(self):
        """TEST 8: Saki cannot answer current query (refusal or temporal inconsistency) -> FINAL_GEMINI_ESCALATION."""
        user_query = "best movies available in 2026"
        stale_draft = "Since I'm currently in the present and the year's still 2023, I cannot tell you about 2026."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=stale_draft,
            action_decision=decision
        )

        assert should_esc is True
        assert reason in ["TEMPORAL_INCONSISTENCY", "SAKI_CANNED_REFUSAL"]

    def test_09_gemini_response_returned_directly(self):
        """TEST 9: Gemini successfully answers -> GEMINI_RESPONSE_RETURNED_DIRECTLY."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Top films released in 2026 include Dune: Part Three and Avatar: Fire and Ash."}]
                    }
                }
            ]
        }

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("best movies available in 2026")

            assert status == "SUCCESS"
            assert "2026" in gemini_ans
            assert "Dune" in gemini_ans

    def test_10_gemini_fails_controlled_failure(self):
        """TEST 10: Gemini fails (500/timeout) -> CONTROLLED_FAILURE."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("best movies available in 2026")

            assert gemini_ans is None
            assert status == "HTTP_500"

    def test_11_no_second_escalation_when_already_attempted(self):
        """TEST 11: Final escalation already attempted -> NO_SECOND_ESCALATION."""
        user_query = "best movies available in 2026"
        draft = "2026 is still in the future."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=draft,
            action_decision=decision,
            already_attempted=True
        )

        assert should_esc is False
        assert reason == "ALREADY_ESCALATED"
