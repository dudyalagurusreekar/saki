"""
Unit and Integration Tests for Relevance Gate
"""

import pytest
from backend.services.evidence_engine import RelevanceGate


def test_kambadur_temple_relevance_matching():
    """Verify that Kambadur search results match a Kambadur query."""
    query = "What is special about Kambadur Temple in Andhra Pradesh?"
    raw_items = [
        {
            "title": "Sri Mallikarjuna Swamy Temple Kambadur AP",
            "snippet": "Malleswara Swamy Siva Temple at Kambadur is an 8th-century heritage site with Chalukyan carvings."
        },
        {
            "title": "Unrelated Temple Wiki",
            "snippet": "This is a temple in another state."
        }
    ]
    
    states = RelevanceGate.evaluate_relevance(query, raw_items)
    assert states[0] == "RELEVANT"
    assert states[1] == "IRRELEVANT"


def test_vijayawada_places_filtering():
    """Verify that unrelated entities/locations like Yelahanka Fort are filtered out for Vijayawada."""
    query = "What are special places in Vijayawada?"
    raw_items = [
        {
            "title": "Kanakadurga Temple Vijayawada",
            "snippet": "Located on Indrakeeladri hill in Vijayawada, Andhra Pradesh."
        },
        {
            "title": "Yelahanka Fort Karnataka",
            "snippet": "Historic fort located in Yelahanka suburb of Bangalore, Karnataka."
        }
    ]
    
    states = RelevanceGate.evaluate_relevance(query, raw_items)
    assert states[0] == "RELEVANT"
    assert states[1] == "IRRELEVANT"


def test_unrelated_entity_rejection():
    """Verify that completely unrelated search results are correctly rejected."""
    query = "Who is the current Python version release manager?"
    raw_items = [
        {
            "title": "Cooking recipes",
            "snippet": "Learn how to make chocolate chip cookies at home easily."
        }
    ]
    
    states = RelevanceGate.evaluate_relevance(query, raw_items)
    assert states[0] == "IRRELEVANT"


def test_uncertain_results_fail_closed():
    """Verify that uncertain results that cannot establish relevance fail closed (rejected)."""
    query = "fastapi streaming response"
    raw_items = [
        {
            "title": "A random tech article",
            "snippet": "This article discusses general software engineering patterns without mentioning python or stream."
        }
    ]
    states = RelevanceGate.evaluate_relevance(query, raw_items)
    assert states[0] == "IRRELEVANT"
