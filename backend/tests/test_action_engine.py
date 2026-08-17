import pytest
from backend.services.action_engine import (
    decide_action,
    classify_freshness,
    ACTION_LOCAL_REASONING,
    ACTION_MEMORY_RECALL,
    ACTION_RAG_RETRIEVAL,
    ACTION_WEB_SEARCH,
    ACTION_WEB_FETCH,
    ACTION_WEB_RESEARCH,
    ACTION_BROWSER_READ,
    ACTION_BROWSER_INTERACT,
    ACTION_VISION,
    ACTION_CODING,
    ACTION_CLARIFICATION,
    FRESHNESS_STABLE,
    FRESHNESS_CURRENT,
    FRESHNESS_LIVE,
    FRESHNESS_USER_EXPLICIT_SEARCH
)
from backend.services.orchestrator import SakiModelOrchestrator


def test_action_stable_factual_question():
    decision = decide_action("What is a binary search tree?")
    assert decision.action == ACTION_LOCAL_REASONING
    assert decision.requires_world_access is False
    assert decision.freshness_requirement == FRESHNESS_STABLE


def test_action_personal_memory_question():
    decision = decide_action("Do you remember what my favorite programming language is?")
    assert decision.action == ACTION_MEMORY_RECALL
    assert decision.requires_memory is True
    assert decision.requires_world_access is False


def test_action_explicit_web_request():
    decision = decide_action("Search online for latest Rust 1.85 features")
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True
    assert decision.requires_fresh_information is True


def test_action_current_information_request():
    decision = decide_action("What is the latest NVIDIA GPU driver version in 2026?")
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True
    assert decision.freshness_requirement in [FRESHNESS_CURRENT, FRESHNESS_USER_EXPLICIT_SEARCH]


def test_action_explicit_webpage_request():
    decision = decide_action("Summarize this page https://docs.python.org/3/whatsnew/3.12.html")
    assert decision.action == ACTION_WEB_FETCH
    assert decision.requires_world_access is True


def test_action_multi_source_comparison():
    decision = decide_action("Compare five current laptop models using multiple sources and deep research")
    assert decision.action == ACTION_WEB_RESEARCH
    assert decision.requires_world_access is True
    assert len(decision.planned_actions) >= 2


def test_action_browser_read_and_interact():
    decision_read = decide_action("Inspect DOM and view web page structure")
    assert decision_read.action == ACTION_BROWSER_READ

    decision_interact = decide_action("Click on submit button and fill form on website")
    assert decision_interact.action == ACTION_BROWSER_INTERACT
    assert decision_interact.requires_user_confirmation is True


def test_action_image_interpretation():
    decision = decide_action("What is shown in this screenshot?", has_image=True)
    assert decision.action == ACTION_VISION
    assert decision.requires_world_access is False


def test_action_coding_request():
    decision = decide_action("Write a FastAPI endpoint with pydantic validation", is_coding=True)
    assert decision.action == ACTION_CODING
    assert decision.requires_world_access is False


def test_action_ambiguous_request():
    decision = decide_action("abc")
    assert decision.action == ACTION_CLARIFICATION
    assert decision.confidence < 0.55


def test_action_unknown_stable_information():
    decision = decide_action("Explain the mathematical definition of Riemannian manifolds")
    assert decision.action == ACTION_LOCAL_REASONING
    assert decision.requires_world_access is False


def test_action_unknown_current_information():
    decision = decide_action("Who is the current CEO of Anthropic today in 2026?")
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True


def test_action_explicit_search_online():
    decision = decide_action("search online for PyTorch CUDA compatibility")
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True


def test_action_memory_sufficient():
    decision = decide_action("What project architecture did I choose?")
    assert decision.action == ACTION_MEMORY_RECALL
    assert decision.requires_memory is True


def test_action_memory_insufficient_plus_current():
    decision = decide_action("What laptop should I buy today with current 2026 deals?")
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access is True


def test_action_multi_action_planning():
    decision = decide_action("Using my previous project decisions, compare multi-source current frameworks")
    assert ACTION_MEMORY_RECALL in decision.planned_actions or ACTION_WEB_RESEARCH in decision.planned_actions


def test_action_orchestrator_integration():
    routing = SakiModelOrchestrator.classify_request("Search online for Python 3.13 features")
    assert routing.action_decision is not None
    assert routing.action_decision.action == ACTION_WEB_SEARCH
    assert routing.action_decision.requires_world_access is True


def test_action_security_validation():
    # 1. Action Engine decision MUST NOT make external network tool calls
    decision = decide_action("Search online for secrets")
    assert decision.action == ACTION_WEB_SEARCH
    # Action decision object produced cleanly without raising or leaking credentials
    assert "chain_of_thought" not in decision.dict()
    assert "private_reasoning" not in decision.dict()
