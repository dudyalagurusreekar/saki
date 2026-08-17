"""
Unit and Integration Tests for Action/Web Routing
"""

import pytest
from backend.services.action_engine import decide_action, ACTION_LOCAL_REASONING, ACTION_WEB_SEARCH


def test_normal_knowledge_routing():
    """Verify that general stable knowledge queries bypass web search and route to local reasoning."""
    query = "What is a neural network and how does backpropagation work?"
    decision = decide_action(query)
    assert decision.action == ACTION_LOCAL_REASONING
    assert not decision.requires_world_access


def test_current_information_routing():
    """Verify that queries for current or latest version/release details trigger web search."""
    query = "What is the latest Python version released in 2026?"
    decision = decide_action(query)
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access


def test_obscure_entity_routing():
    """Verify that obscure or unfamiliar local entities (like Kambadur Temple) trigger mandatory web search."""
    query = "Where is Kambadur Temple located?"
    decision = decide_action(query)
    assert decision.action == ACTION_WEB_SEARCH
    assert decision.requires_world_access
