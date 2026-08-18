"""
Regression and Integration Tests for Saki's Grounded Web Search Pipeline
Validates hallucination prevention, relevance gating, explicit provider status,
refusal directives, state transitions, and diagnostic trace generation.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.evidence_engine import (
    RelevanceGate,
    EvidenceIntelligenceEngine,
    EVIDENCE_STATUS_INSUFFICIENT,
    EVIDENCE_STATUS_SUFFICIENT
)
from backend.services.world_access_manager import (
    WorldAccessManager,
    EvidenceEngine,
    DiagnosticTracer
)
from backend.services.action_engine import (
    decide_action,
    ActionDecision,
    ACTION_WEB_SEARCH,
    ACTION_LOCAL_REASONING
)
from backend.services.gemini_search import GeminiSearchProvider


# =====================================================================
# SCENARIO 1: Kambadur Temple Refusal (No Hallucination of Tadipatri/Godavari)
# =====================================================================
def test_kambadur_refusal_on_unrelated_search_results():
    """
    Scenario: User asks about Kambadur Temple in Andhra Pradesh.
    Search returns only unrelated results (e.g. Tadipatri town overview).
    Expected: Relevance gate drops Tadipatri result; EvidenceEngine sets status=INSUFFICIENT;
    Saki emits refusal instruction without inventing facts.
    """
    query = "What is special about Kambadur Temple in Andhra Pradesh?"
    raw_results = [
        {
            "title": "Tadipatri Overview",
            "snippet": "Tadipatri is a town in Anantapur district of Andhra Pradesh famous for Chintala Venkataramana Temple.",
            "url": "https://en.wikipedia.org/wiki/Tadipatri",
            "domain": "en.wikipedia.org"
        }
    ]

    # Evaluate relevance gate directly
    relevance_states = RelevanceGate.evaluate_relevance(query, raw_results)
    assert relevance_states[0] == "IRRELEVANT"

    # Synthesize evidence package
    package = EvidenceIntelligenceEngine.process_and_synthesize(
        query=query,
        raw_items=raw_results
    )
    assert package.evidence_status == EVIDENCE_STATUS_INSUFFICIENT
    assert len(package.claims) == 0
    assert package.evidence_items[0].process_state == "IRRELEVANT"

    # Verify formatted prompt block contains insufficient evidence / refusal notice
    prompt_block = EvidenceIntelligenceEngine.format_grounded_prompt_block(package)
    assert "Insufficient external evidence" in prompt_block


# =====================================================================
# SCENARIO 2: Vijayawada Places (Filter out Yelahanka Fort / Bangalore)
# =====================================================================
def test_vijayawada_places_filtering():
    """
    Scenario: User asks for special places in Vijayawada.
    Search returns Kanakadurga Temple (Vijayawada) and Yelahanka Fort (Bangalore).
    Expected: Yelahanka Fort is marked IRRELEVANT and excluded from claims/prompt.
    """
    query = "What are special places in Vijayawada?"
    raw_results = [
        {
            "title": "Kanaka Durga Temple Vijayawada",
            "snippet": "Located on Indrakeeladri hill in Vijayawada along the banks of Krishna River.",
            "url": "https://ap.gov.in/kanakadurgatemple",
            "domain": "ap.gov.in"
        },
        {
            "title": "Yelahanka Fort Overview",
            "snippet": "Historic fort located in Yelahanka suburb of Bangalore, Karnataka.",
            "url": "https://en.wikipedia.org/wiki/Yelahanka_Fort",
            "domain": "en.wikipedia.org"
        }
    ]

    package = EvidenceIntelligenceEngine.process_and_synthesize(
        query=query,
        raw_items=raw_results
    )

    assert package.evidence_status == EVIDENCE_STATUS_SUFFICIENT
    assert package.evidence_items[0].process_state == "RELEVANT"
    assert package.evidence_items[1].process_state == "IRRELEVANT"

    prompt_block = EvidenceIntelligenceEngine.format_grounded_prompt_block(package)
    assert "Kanaka Durga Temple" in prompt_block
    assert "Yelahanka" not in prompt_block


# =====================================================================
# SCENARIO 3: Known Conceptual Fact (No Web Search Triggered)
# =====================================================================
def test_known_conceptual_fact_no_search():
    """
    Scenario: User asks 'What is a neural network?'
    Expected: Action engine resolves to local reasoning without world access.
    """
    query = "What is a neural network?"
    decision = decide_action(query)
    assert decision.requires_world_access is False
    assert decision.action == ACTION_LOCAL_REASONING


# =====================================================================
# SCENARIO 4: Current Information Query (Triggers Web Search with Provider Status)
# =====================================================================
def test_current_info_triggers_search_with_provider_status():
    """
    Scenario: User asks 'What is the latest version of Python?'
    Expected: Action engine resolves to web search; Gemini search provider returns SUCCESS status.
    """
    query = "What is the latest version of Python?"
    decision = decide_action(query)
    assert decision.requires_world_access is True
    assert decision.action in [ACTION_WEB_SEARCH, "WEB_RESEARCH"]

    mock_gemini_resp = [
        {
            "title": "Python 3.12 Release Notes",
            "snippet": "Python 3.12.0 is the latest stable release.",
            "url": "https://www.python.org/downloads/",
            "domain": "python.org",
            "provider": "Google Search (Gemini Grounded)",
            "provider_status": "SUCCESS",
            "fallback_from": None,
            "error_detail": None
        }
    ]
    with patch("backend.services.gemini_search.GeminiSearchProvider.search", return_value=mock_gemini_resp):
        items, prompt_block = WorldAccessManager.execute_action(decision, query)
        assert len(items) == 1
        assert items[0].provenance["provider_status"] == "SUCCESS"
        assert "python.org" in prompt_block


# =====================================================================
# SCENARIO 5: Explicit Verification Request (Verification Mode State Transition)
# =====================================================================
def test_explicit_verification_mode_state_transition():
    """
    Scenario: User asks 'Verify this information about climate change.'
    Expected: Action engine detects verification intent; claims transition to VERIFIED status.
    """
    query = "Verify whether global temperatures increased in 2025."
    action = ActionDecision(
        action=ACTION_WEB_SEARCH,
        reason="User requested verification",
        requires_world_access=True,
        query_intent="verification"
    )

    raw_items = [
        {
            "title": "NASA Climate Observation",
            "snippet": "Global surface temperature records confirm an increase in global temperatures in 2025.",
            "url": "https://nasa.gov/climate",
            "domain": "nasa.gov",
            "provider": "Google Search (Gemini Grounded)",
            "provider_status": "SUCCESS"
        }
    ]

    with patch("backend.services.gemini_search.GeminiSearchProvider.search", return_value=raw_items):
        items, prompt_block, package = WorldAccessManager.execute_action_package(action, query)
        assert package is not None
        assert len(package.claims) > 0
        assert package.claims[0].support_status == "VERIFIED"


# =====================================================================
# SCENARIO 6: Unknown Entity Query ("FooBarBaz" Refusal)
# =====================================================================
def test_unknown_entity_refusal():
    """
    Scenario: User asks 'Tell me about the city FooBarBaz'.
    Expected: Fail-closed gate drops unrelated hits; package status is INSUFFICIENT.
    """
    query = "Tell me about the city FooBarBaz"
    raw_results = [
        {
            "title": "Random Wikipedia Article",
            "snippet": "This article discusses General Relativity and quantum physics concepts.",
            "url": "https://en.wikipedia.org/wiki/Physics",
            "domain": "en.wikipedia.org"
        }
    ]

    package = EvidenceIntelligenceEngine.process_and_synthesize(
        query=query,
        raw_items=raw_results
    )
    assert package.evidence_status == EVIDENCE_STATUS_INSUFFICIENT
    assert len(package.claims) == 0


# =====================================================================
# SCENARIO 7: Diagnostic Trace Format & Auditing
# =====================================================================
def test_diagnostic_trace_generation():
    """
    Scenario: Execute web search via WorldAccessManager.
    Expected: DiagnosticTracer outputs structured trace dictionary containing all required audit fields.
    """
    query = "What is special about Kambadur Temple in Andhra Pradesh?"
    action = ActionDecision(
        action=ACTION_WEB_SEARCH,
        reason="Search query",
        requires_world_access=True
    )
    raw_items = [
        {
            "title": "Tadipatri Overview",
            "snippet": "Tadipatri is a town in Anantapur district.",
            "url": "https://en.wikipedia.org/wiki/Tadipatri",
            "domain": "en.wikipedia.org",
            "provider": "gemini",
            "provider_status": "SUCCESS"
        }
    ]

    with patch("backend.services.gemini_search.GeminiSearchProvider.search", return_value=raw_items):
        items, block, package = WorldAccessManager.execute_action_package(action, query)
        trace = getattr(WorldAccessManager, "_last_diagnostic_trace", None)
        assert trace is not None
        assert trace["USER_QUERY"] == query
        assert trace["ACTION"] == ACTION_WEB_SEARCH
        assert trace["SEARCH_PROVIDER"] == "gemini"
        assert trace["PROVIDER_STATUS"] == "SUCCESS"
        assert "Tadipatri Overview" in trace["REJECTED_SOURCES"]
