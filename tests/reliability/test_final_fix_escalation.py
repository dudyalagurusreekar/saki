"""
Final Fix Automated Test Suite: Current-Query Failure Must Escalate to Gemini
Covers Tests 1-10 required by Final Fix specifications.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.action_engine import (
    classify_freshness,
    parse_query_understanding,
    decide_action,
    FRESHNESS_CURRENT,
    FRESHNESS_STABLE
)
from backend.services.gemini_escalation import GeminiEscalationEngine
from backend.services.evidence_engine import EvidencePackage, EVIDENCE_STATUS_SUFFICIENT, EVIDENCE_STATUS_INSUFFICIENT
from backend.services.response_evaluator import EvaluationResult
from backend.services.grounding_verifier import AnswerGroundingAssessment
from backend.routes.chat import ChatRequest, chat


class TestFinalFixCurrentQueryEscalation:
    """Automated tests for current-query draft validation and last-resort escalation."""

    def test_01_runtime_2026_movies_in_2026_is_current_year(self):
        """TEST 1: runtime = 2026, query: 'best movies to watch in 2026' -> CURRENT_YEAR / CURRENT."""
        freshness = classify_freshness("best movies to watch in 2026", runtime_year=2026)
        assert freshness == FRESHNESS_CURRENT

        decision = decide_action("best movies to watch in 2026")
        assert decision.requires_world_access is True
        assert decision.freshness_requirement == FRESHNESS_CURRENT

    def test_02_draft_2026_is_in_the_future_is_invalid_current_draft(self):
        """TEST 2: draft: '2026 is in the future' -> INVALID_CURRENT_DRAFT."""
        draft = "2026 is in the future so I cannot recommend films yet."
        is_invalid, reason = GeminiEscalationEngine.is_invalid_current_draft(
            draft_text=draft,
            user_query="best movies to watch in 2026",
            is_current_query=True,
            runtime_year=2026
        )

        assert is_invalid is True
        assert "TEMPORAL" in reason or "INSUFFICIENCY" in reason

    def test_03_draft_cannot_tap_into_the_future_is_invalid_current_draft(self):
        """TEST 3: draft: 'Since I can't tap into the future to check the latest flicks, how about we reminisce on classics...' -> INVALID_CURRENT_DRAFT."""
        draft = "Hey there! Since I can't tap into the future to check the latest flicks, how about we reminisce on classics that have stood the test of time, or explore some indie gems that have been making waves lately? What are your vibes? 😊"
        is_invalid, reason = GeminiEscalationEngine.is_invalid_current_draft(
            draft_text=draft,
            user_query="best movies to watch in 2026",
            is_current_query=True,
            runtime_year=2026
        )

        assert is_invalid is True
        assert "TEMPORAL" in reason or "INSUFFICIENCY" in reason

    def test_04_current_query_plus_invalid_current_draft_triggers_escalation(self):
        """TEST 4: current query + invalid current draft -> FINAL_GEMINI_ESCALATION."""
        user_query = "best movies to watch in 2026"
        draft = "Since I can't tap into the future to check the latest flicks, how about we reminisce on classics?"
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=draft,
            action_decision=decision
        )

        assert should_esc is True
        assert reason in ["INVALID_CURRENT_DRAFT", "TEMPORAL_INCONSISTENCY", "SAKI_CANNED_REFUSAL"]

    def test_05_gemini_succeeds_returned_directly(self):
        """TEST 5: Gemini succeeds -> Gemini response returned directly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Top films released in 2026 include The Odyssey and Solaris Reborn."}]
                    }
                }
            ]
        }

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("best movies to watch in 2026")

            assert status == "SUCCESS"
            assert "The Odyssey" in gemini_ans
            assert latency >= 0.0

    def test_06_gemini_fails_controlled_failure(self):
        """TEST 6: Gemini fails -> controlled failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("best movies to watch in 2026")

            assert gemini_ans is None
            assert status == "HTTP_500"

    def test_07_latest_fastapi_version_web_failure_triggers_escalation(self):
        """TEST 7: latest FastAPI version + normal web failure -> final Gemini escalation."""
        user_query = "latest FastAPI version"
        draft = "I don't have verified records or active web search results to confirm the current version of FastAPI."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=draft,
            action_decision=decision
        )

        assert should_esc is True

    def test_08_what_is_fastapi_normal_saki_answer_no_escalation(self):
        """TEST 8: what is FastAPI? + normal Saki answer -> NO_FINAL_ESCALATION."""
        user_query = "what is FastAPI"
        draft = "FastAPI is a modern, high-performance web framework for building APIs with Python."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=draft,
            action_decision=decision
        )

        assert should_esc is False
        assert reason == "SAKI_ANSWERED_NORMALLY"

    def test_09_normal_web_succeeds_no_escalation(self):
        """TEST 9: normal web succeeds with verified evidence -> NO_FINAL_ESCALATION."""
        user_query = "latest FastAPI version"
        draft = "FastAPI 0.115.0 was released in 2026 with full Pydantic v2 support."
        decision = decide_action(user_query)
        evidence_pkg = EvidencePackage(
            query=user_query,
            retrieved_at=100.0,
            evidence_status=EVIDENCE_STATUS_SUFFICIENT
        )
        eval_res = EvaluationResult(
            plan=None,
            mode="TECHNICAL",
            repaired_text=draft,
            grounding_assessment=AnswerGroundingAssessment(
                grounding_status="FULLY_SUPPORTED",
                supported_claims=1,
                unsupported_claims=0
            )
        )

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=draft,
            eval_result=eval_res,
            evidence_package=evidence_pkg,
            action_decision=decision
        )

        assert should_esc is False

    def test_10_final_escalation_already_attempted_no_second_escalation(self):
        """TEST 10: final escalation already attempted -> NO_SECOND_ESCALATION."""
        user_query = "best movies to watch in 2026"
        draft = "Since I can't tap into the future to check the latest flicks, how about we reminisce on classics?"
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=draft,
            action_decision=decision,
            already_attempted=True
        )

        assert should_esc is False
        assert reason == "ALREADY_ESCALATED"
