import pytest
from unittest.mock import patch
from backend.core.config import settings
from backend.services.search_service import safe_search


def test_privacy_mode_high_blocks_search():
    with patch.object(settings, "PRIVACY_MODE", "HIGH"):
        results = safe_search("Who won the 2026 World Cup?")
        assert results == []


def test_safe_search_fallback_privacy():
    with patch("backend.core.privacy.PrivacyPolicyEngine.evaluate_request") as mock_eval:
        from backend.core.privacy import PrivacyDecision, DECISION_BLOCK
        mock_eval.return_value = PrivacyDecision(decision=DECISION_BLOCK, reason="Blocked for test")
        results = safe_search("sensitive personal question")
        assert results == []

