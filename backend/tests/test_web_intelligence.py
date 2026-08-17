import pytest
from backend.services.web_intelligence import (
    WebIntelligenceCapability,
    WebIntelligenceResult,
    FRESH_CURRENT,
    MAX_SEARCHES,
    MAX_PAGES
)


# -------------------------
# QUERY REFINEMENT & SANITIZATION TESTS
# -------------------------
def test_query_refinement_and_privacy_sanitization():
    queries = WebIntelligenceCapability.refine_queries("How to implement FastAPI streaming responses")
    
    assert isinstance(queries, list)
    assert len(queries) <= MAX_SEARCHES
    assert any("fastapi" in q.lower() for q in queries)


# -------------------------
# PRIMARY SOURCE PRIORITIZATION TEST
# -------------------------
def test_primary_source_prioritization():
    raw_results = [
        {"url": "https://randomblog.com/post1", "title": "Random Blog", "snippet": "FastAPI tips"},
        {"url": "https://fastapi.tiangolo.com/docs", "title": "Official FastAPI Docs", "snippet": "Official guide"}
    ]
    ranked = WebIntelligenceCapability.prioritize_primary_sources(raw_results)
    
    assert ranked[0]["url"] == "https://fastapi.tiangolo.com/docs"
    assert ranked[0]["is_primary"] is True


# -------------------------
# WEB INTELLIGENCE EXECUTION TEST
# -------------------------
def test_execute_web_intelligence_pipeline():
    res = WebIntelligenceCapability.execute_web_intelligence("FastAPI official documentation")
    
    assert isinstance(res, WebIntelligenceResult)
    assert len(res.queries_executed) <= MAX_SEARCHES
    assert res.freshness_status == FRESH_CURRENT
    assert res.unified_package is not None
