"""
Unit and Integration Tests for Saki Gemini Search Grounding & Real-Time Web Intelligence
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.core.config import settings
from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.gemini_search import GeminiSearchProvider
from backend.services.world_access_manager import WorldAccessManager, EvidenceEngine, DuckDuckGoSearchProvider
from backend.services.evidence_engine import EvidenceIntelligenceEngine, EvidencePackage, EvidenceItem
from backend.services.web_intelligence import WebIntelligenceCapability, WebIntelligenceResult
from backend.services.action_engine import ActionDecision, ACTION_WEB_SEARCH, ACTION_WEB_RESEARCH, classify_freshness, FRESHNESS_CURRENT


# -------------------------
# 1. GEMINI LIVE & EXTRACTION TESTS
# -------------------------
def test_gemini_search_provider_live_query():
    """Verify GeminiSearchProvider executes live search with Google Search grounding."""
    results = GeminiSearchProvider.search("FastAPI documentation streaming response", max_results=3)
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert "title" in first
    assert "snippet" in first
    assert "url" in first
    assert "domain" in first
    assert "provider" in first


def test_gemini_search_grounded_package_extraction():
    """Verify GeminiSearchProvider.search_grounded extracts grounded summary and web queries."""
    res = GeminiSearchProvider.search_grounded("Python current release version", max_results=2)
    assert "grounded_summary" in res
    assert "web_search_queries" in res
    assert "sources" in res
    assert isinstance(res["sources"], list)
    assert len(res["sources"]) > 0


# -------------------------
# 2. RESILIENT FALLBACK TESTS
# -------------------------
def test_gemini_search_fallback_when_disabled():
    """Verify automatic fallback to DuckDuckGo when Gemini is disabled."""
    with patch.object(settings, "ENABLE_GEMINI_SEARCH", False):
        results = GeminiSearchProvider.search("Python 3.12 documentation", max_results=2)
        assert len(results) > 0
        assert "title" in results[0]


def test_gemini_search_fallback_on_api_error():
    """Verify automatic fallback to DuckDuckGo when Gemini API returns an error or raises an exception."""
    with patch("httpx.Client.post", side_effect=Exception("Connection timeout")):
        results = GeminiSearchProvider.search("React 19 release features", max_results=2)
        assert len(results) > 0
        assert "title" in results[0]


# -------------------------
# 3. WORLD ACCESS & EVIDENCE ENGINE INTEGRATION
# -------------------------
def test_world_access_manager_with_gemini_provider():
    """Verify WorldAccessManager executes action package with Gemini search provider."""
    decision = ActionDecision(
        action=ACTION_WEB_SEARCH,
        requires_world_access=True,
        requires_fresh_information=True,
        freshness_requirement=FRESHNESS_CURRENT
    )
    items, prompt_block, package = WorldAccessManager.execute_action_package(
        decision,
        "What is FastAPI official documentation url?"
    )
    assert len(items) > 0
    assert "<external_web_content>" in prompt_block
    assert "</external_web_content>" in prompt_block
    assert package is not None
    assert isinstance(package, EvidencePackage)
    assert len(package.sources) > 0


def test_web_intelligence_capability_with_gemini_grounding():
    """Verify WebIntelligenceCapability returns verified EvidencePackage and UnifiedKnowledgePackage."""
    intel_res = WebIntelligenceCapability.execute_web_intelligence("FastAPI official documentation")
    assert isinstance(intel_res, WebIntelligenceResult)
    assert len(intel_res.queries_executed) > 0
    assert intel_res.unified_package is not None
    assert intel_res.unified_package.total_candidates > 0


# -------------------------
# 4. PRIVACY BOUNDARY ENFORCEMENT
# -------------------------
def test_privacy_gate_blocks_secret_outbound_gemini_search():
    """Verify PrivacyPolicyEngine blocks secret keys from ever reaching external search."""
    secret_query = "Find API key for secret AIzaSyBJej43jDBLEVqbjp4GH6UfSRktBl6hrnc"
    req = OutboundRequest(query=secret_query, action="WEB_SEARCH")
    decision = PrivacyPolicyEngine.evaluate_request(req)
    assert decision.decision == DECISION_BLOCK


# -------------------------
# 5. FRESHNESS REASONING INTEGRATION
# -------------------------
def test_action_engine_freshness_classification():
    """Verify freshness classification accurately triggers for release versions and 2026 facts."""
    assert classify_freshness("What is the current version of FastAPI in 2026?") == FRESHNESS_CURRENT
    assert classify_freshness("Who is the current CEO of Microsoft?") == FRESHNESS_CURRENT
    assert classify_freshness("What is the definition of binary search?") != FRESHNESS_CURRENT
