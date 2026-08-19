"""
Sprint Final Automated Test Suite: Last-Resort Gemini Answer Escalation
Covers Tests 1-10 required by Sprint Final specifications.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.gemini_escalation import GeminiEscalationEngine
from backend.services.action_engine import parse_query_understanding, decide_action
from backend.services.evidence_engine import EvidencePackage, EVIDENCE_STATUS_SUFFICIENT, EVIDENCE_STATUS_INSUFFICIENT
from backend.services.response_evaluator import EvaluationResult
from backend.services.grounding_verifier import AnswerGroundingAssessment
from backend.routes.chat import ChatRequest, chat


class TestSprintFinalGeminiEscalation:
    """Automated tests for Last-Resort Gemini Answer Escalation."""

    def test_01_normal_answer_exists_no_escalation(self):
        """TEST 1: Normal answer exists. Expected: no final escalation."""
        user_query = "what is FastAPI"
        final_response = "FastAPI is a modern, fast, web framework for building APIs with Python."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            action_decision=decision
        )

        assert should_esc is False
        assert reason == "SAKI_ANSWERED_NORMALLY"

    def test_02_saki_cannot_answer_escalation_occurs(self):
        """TEST 2: Saki cannot answer (canned refusal). Expected: final escalation occurs."""
        user_query = "latest FastAPI version"
        final_response = "I'm sorry, but I don't have verified records or active web search results to confirm the current version of FastAPI."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            action_decision=decision
        )

        assert should_esc is True
        assert "REFUSAL" in reason or "INSUFFICIENT" in reason

    def test_03_gemini_answers_successfully_returned_directly(self):
        """TEST 3: Gemini answers successfully. Expected: Gemini response returned directly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "The latest stable version of FastAPI is 0.115.0."}]
                    }
                }
            ]
        }

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("latest FastAPI version")

            assert status == "SUCCESS"
            assert gemini_ans == "The latest stable version of FastAPI is 0.115.0."
            assert latency >= 0.0

    def test_04_gemini_fails_controlled_failure(self):
        """TEST 4: Gemini fails (HTTP 429). Expected: controlled failure."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Quota exceeded"

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("latest FastAPI version")

            assert gemini_ans is None
            assert status == "HTTP_429"

    def test_05_gemini_returns_empty_response_controlled_failure(self):
        """TEST 5: Gemini returns empty response. Expected: controlled failure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"candidates": []}

        with patch("httpx.Client.post", return_value=mock_response):
            gemini_ans, status, latency = GeminiEscalationEngine.escalate_to_gemini("latest FastAPI version")

            assert gemini_ans is None
            assert status == "EMPTY_GEMINI_RESPONSE"

    def test_06_final_escalation_already_attempted_no_second_escalation(self):
        """TEST 6: Final escalation already attempted. Expected: no second escalation."""
        user_query = "latest FastAPI version"
        final_response = "I don't have verified records."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            action_decision=decision,
            already_attempted=True
        )

        assert should_esc is False
        assert reason == "ALREADY_ESCALATED"

    def test_07_normal_web_pipeline_succeeds_no_escalation(self):
        """TEST 7: Normal web pipeline succeeds with verified evidence. Expected: no escalation."""
        user_query = "latest FastAPI version"
        final_response = "The latest FastAPI version is 0.115.0 based on release notes."
        decision = decide_action(user_query)
        evidence_pkg = EvidencePackage(
            query=user_query,
            retrieved_at=100.0,
            evidence_status=EVIDENCE_STATUS_SUFFICIENT
        )
        eval_res = EvaluationResult(
            plan=None,
            mode="TECHNICAL",
            repaired_text=final_response,
            grounding_assessment=AnswerGroundingAssessment(
                grounding_status="FULLY_SUPPORTED",
                supported_claims=1,
                unsupported_claims=0
            )
        )

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            eval_result=eval_res,
            evidence_package=evidence_pkg,
            action_decision=decision
        )

        assert should_esc is False

    def test_08_normal_web_pipeline_fails_escalation_occurs(self):
        """TEST 8: Normal web pipeline fails (insufficient evidence & canned refusal). Expected: escalation occurs."""
        user_query = "latest FastAPI version"
        final_response = "I don't have verified records or active web search results to confirm this."
        decision = decide_action(user_query)
        evidence_pkg = EvidencePackage(
            query=user_query,
            retrieved_at=100.0,
            evidence_status=EVIDENCE_STATUS_INSUFFICIENT
        )
        eval_res = EvaluationResult(
            plan=None,
            mode="TECHNICAL",
            repaired_text=final_response,
            grounding_assessment=AnswerGroundingAssessment(
                grounding_status="INSUFFICIENT_EVIDENCE",
                supported_claims=0,
                unsupported_claims=0
            )
        )

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            eval_result=eval_res,
            evidence_package=evidence_pkg,
            action_decision=decision
        )

        assert should_esc is True

    def test_09_what_is_fastapi_static_response_no_escalation(self):
        """TEST 9: 'what is FastAPI?'. Expected: normal Saki response, no escalation."""
        user_query = "what is FastAPI"
        final_response = "FastAPI is a Python web framework designed for high-performance API development."
        decision = decide_action(user_query)

        should_esc, reason = GeminiEscalationEngine.should_escalate(
            user_query=user_query,
            final_response=final_response,
            action_decision=decision
        )

        assert should_esc is False

    def test_10_latest_fastapi_version_gemini_answer_reaches_user_directly(self):
        """TEST 10: 'latest FastAPI version' reaches user directly when Saki cannot answer and Gemini succeeds."""
        mock_gemini_text = "As of 2026, the latest version of FastAPI is 0.115.0, featuring Pydantic v2 integration."
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": mock_gemini_text}]
                    }
                }
            ]
        }

        # Mock call_model to return a canned refusal
        with patch("backend.routes.chat.call_model", return_value="I'm sorry, but I don't have verified records or active web search results to confirm the current version of FastAPI."):
            with patch("httpx.Client.post", return_value=mock_response):
                req = ChatRequest(message="latest FastAPI version", conversation_id="test-escalation-10")
                chat_res = chat(req)

                assert chat_res.response == mock_gemini_text
                assert "I don't have verified records" not in chat_res.response
