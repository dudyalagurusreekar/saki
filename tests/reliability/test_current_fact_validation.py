"""
Test Suite for Current-Fact Validation & Temporal Invariant Fixes
Covers all 12 required test specifications:
TEST 1: 'what is Python?' -> STATIC
TEST 2: 'what is current Python version?' -> CURRENT_EXTERNAL_FACT
TEST 3: 'latest FastAPI version' -> CURRENT_EXTERNAL_FACT
TEST 4: 'latest Node.js version' -> CURRENT_EXTERNAL_FACT
TEST 5: 'latest Ollama version' -> CURRENT_EXTERNAL_FACT
TEST 6: 'what time is it?' -> CURRENT_TIME
TEST 7: 'what is today\'s date?' -> CURRENT_DATE
TEST 8: current version query + no external evidence + stale model answer -> ANSWER_REJECTED
TEST 9: current version query + normal web failure -> FINAL_GEMINI_ESCALATION
TEST 10: Gemini succeeds -> Gemini response returned directly
TEST 11: normal web succeeds -> NO unnecessary final Gemini escalation
TEST 12: Gemini already attempted -> NO second escalation
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.action_engine import (
    classify_freshness,
    decide_action,
    is_current_external_fact_query,
    is_current_time_query,
    FRESHNESS_STABLE,
    FRESHNESS_CURRENT_EXTERNAL_FACT,
    FRESHNESS_CURRENT,
    ACTION_LOCAL_REASONING,
    ACTION_WEB_SEARCH
)
from backend.services.gemini_escalation import GeminiEscalationEngine
from backend.services.evidence_engine import EvidencePackage, EvidenceItem


# ==========================================
# PART 18 TEST 1: STATIC KNOWLEDGE
# ==========================================
def test_1_what_is_python_is_static():
    query = "what is Python?"
    freshness = classify_freshness(query)
    decision = decide_action(query)
    
    assert freshness == FRESHNESS_STABLE, f"Expected {FRESHNESS_STABLE}, got {freshness}"
    assert decision.action == ACTION_LOCAL_REASONING, f"Expected {ACTION_LOCAL_REASONING}, got {decision.action}"
    assert decision.requires_world_access is False
    assert is_current_external_fact_query(query) is False


# ==========================================
# PART 18 TEST 2: CURRENT PYTHON VERSION
# ==========================================
def test_2_current_python_version_is_current_external_fact():
    query = "what is current Python version?"
    freshness = classify_freshness(query)
    decision = decide_action(query)
    
    assert freshness == FRESHNESS_CURRENT_EXTERNAL_FACT, f"Expected {FRESHNESS_CURRENT_EXTERNAL_FACT}, got {freshness}"
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True
    assert decision.freshness_requirement == FRESHNESS_CURRENT_EXTERNAL_FACT
    assert is_current_external_fact_query(query) is True


# ==========================================
# PART 18 TEST 3: LATEST FASTAPI VERSION
# ==========================================
def test_3_latest_fastapi_version_is_current_external_fact():
    query = "latest FastAPI version"
    freshness = classify_freshness(query)
    decision = decide_action(query)
    
    assert freshness == FRESHNESS_CURRENT_EXTERNAL_FACT, f"Expected {FRESHNESS_CURRENT_EXTERNAL_FACT}, got {freshness}"
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True
    assert is_current_external_fact_query(query) is True


# ==========================================
# PART 18 TEST 4: LATEST NODE.JS VERSION
# ==========================================
def test_4_latest_nodejs_version_is_current_external_fact():
    query = "latest Node.js version"
    freshness = classify_freshness(query)
    decision = decide_action(query)
    
    assert freshness == FRESHNESS_CURRENT_EXTERNAL_FACT, f"Expected {FRESHNESS_CURRENT_EXTERNAL_FACT}, got {freshness}"
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True
    assert is_current_external_fact_query(query) is True


# ==========================================
# PART 18 TEST 5: LATEST OLLAMA VERSION
# ==========================================
def test_5_latest_ollama_version_is_current_external_fact():
    query = "latest Ollama version"
    freshness = classify_freshness(query)
    decision = decide_action(query)
    
    assert freshness == FRESHNESS_CURRENT_EXTERNAL_FACT, f"Expected {FRESHNESS_CURRENT_EXTERNAL_FACT}, got {freshness}"
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True
    assert is_current_external_fact_query(query) is True


# ==========================================
# PART 18 TEST 6: WHAT TIME IS IT?
# ==========================================
def test_6_what_time_is_it_uses_runtime_clock():
    query = "what time is it?"
    assert is_current_time_query(query) is True
    assert is_current_external_fact_query(query) is False


# ==========================================
# PART 18 TEST 7: WHAT IS TODAY'S DATE?
# ==========================================
def test_7_what_is_todays_date_uses_runtime_clock():
    query = "what is today's date?"
    assert is_current_time_query(query) is True
    assert is_current_external_fact_query(query) is False


# ==========================================
# PART 18 TEST 8: STALE MODEL ANSWER REJECTION
# ==========================================
def test_8_stale_model_answer_is_rejected():
    user_query = "what is current python version inmarket"
    stale_model_response = "The latest version of Python available from the official Python website is 3.11."
    decision = decide_action(user_query)

    # With NO external evidence provided, a version claim must be identified as stale
    is_stale, reason = GeminiEscalationEngine.is_stale_current_fact_answer(
        draft_text=stale_model_response,
        user_query=user_query,
        evidence_items=[],
        evidence_package=None,
        action_decision=decision
    )
    assert is_stale is True, "Stale version claim should be rejected"
    assert "STALE_VERSION_CLAIM" in reason

    should_esc, esc_reason = GeminiEscalationEngine.should_escalate(
        user_query=user_query,
        final_response=stale_model_response,
        action_decision=decision,
        evidence_items=[]
    )
    assert should_esc is True, "Stale version claim should trigger escalation"


# ==========================================
# PART 18 TEST 9: NORMAL WEB FAILURE -> ESCALATION
# ==========================================
def test_9_normal_web_failure_triggers_escalation():
    user_query = "what is current python version"
    refusal_response = "I don't have verified records or active web search results to answer this query."
    decision = decide_action(user_query)
    
    empty_ev_pkg = MagicMock(evidence_status="INSUFFICIENT")

    should_esc, esc_reason = GeminiEscalationEngine.should_escalate(
        user_query=user_query,
        final_response=refusal_response,
        action_decision=decision,
        evidence_package=empty_ev_pkg,
        evidence_items=[]
    )
    assert should_esc is True, f"Expected escalation on web failure, got {should_esc} ({esc_reason})"


# ==========================================
# PART 18 TEST 10: GEMINI SUCCEEDS -> DIRECT RETURN
# ==========================================
def test_10_gemini_succeeds_returns_directly():
    user_query = "what is current python version"
    mock_gemini_response = "Python 3.13 is the latest stable release."
    
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "candidates": [{
                    "content": {
                        "parts": [{"text": mock_gemini_response}]
                    }
                }]
            }
        )
        
        with patch("backend.core.config.settings.GEMINI_API_KEY", "mock_key"):
            text, status, lat = GeminiEscalationEngine.escalate_to_gemini(user_query)
            assert status == "SUCCESS"
            assert text == mock_gemini_response


# ==========================================
# PART 18 TEST 11: NORMAL WEB SUCCEEDS -> NO UNNECESSARY ESCALATION
# ==========================================
def test_11_normal_web_succeeds_no_escalation():
    user_query = "what is current python version"
    decision = decide_action(user_query)
    
    # Saki generated a valid grounded answer backed by real evidence
    grounded_response = "According to official Python releases, Python 3.13 is the current stable version."
    
    mock_ev_item = MagicMock(
        title="Python 3.13 Release",
        snippet="Python 3.13.0 is the latest stable release",
        url="https://www.python.org/downloads/",
        domain="python.org"
    )
    mock_ev_pkg = MagicMock(evidence_status="GROUNDED")
    mock_eval = MagicMock(grounding_assessment=MagicMock(grounding_status="GROUNDED"))

    should_esc, esc_reason = GeminiEscalationEngine.should_escalate(
        user_query=user_query,
        final_response=grounded_response,
        eval_result=mock_eval,
        evidence_package=mock_ev_pkg,
        action_decision=decision,
        evidence_items=[mock_ev_item]
    )
    assert should_esc is False, f"Expected no escalation when web succeeds, got: {esc_reason}"


# ==========================================
# PART 18 TEST 12: ALREADY ATTEMPTED -> NO SECOND ESCALATION
# ==========================================
def test_12_already_attempted_no_second_escalation():
    user_query = "what is current python version"
    response = "I don't have verified records."
    decision = decide_action(user_query)

    should_esc, esc_reason = GeminiEscalationEngine.should_escalate(
        user_query=user_query,
        final_response=response,
        action_decision=decision,
        already_attempted=True
    )
    assert should_esc is False
    assert esc_reason == "ALREADY_ESCALATED"
