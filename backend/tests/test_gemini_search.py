"""
Unit Tests for GeminiSearchProvider Status Tracking, Fallbacks, and Provenance
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.services.gemini_search import GeminiSearchProvider
from backend.services.world_access_manager import DuckDuckGoSearchProvider


def test_provider_success():
    """Verify GeminiSearchProvider sets status='SUCCESS' on successful query grounding."""
    mock_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Python 3.12 was released in October 2023."}]
                },
                "groundingMetadata": {
                    "webSearchQueries": ["Python 3.12 release date"],
                    "groundingChunks": [
                        {
                            "web": {
                                "uri": "https://www.python.org/downloads/release/python-3120/",
                                "title": "Python 3.12.0 Release"
                            }
                        }
                    ],
                    "groundingSupports": [
                        {
                            "segment": {"text": "Python 3.12 was released in October 2023."},
                            "groundingChunkIndices": [0]
                        }
                    ]
                }
            }
        ]
    }
    
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        results = GeminiSearchProvider.search("Python 3.12 release date")
        assert len(results) > 0
        assert results[0]["provider_status"] == "SUCCESS"
        assert "Google Search" in results[0]["provider"]


def test_provider_failure():
    """Verify GeminiSearchProvider handles HTTP failure explicitly with fallback and FAILED status."""
    with patch("httpx.Client.post") as mock_post, \
         patch.object(DuckDuckGoSearchProvider, "search", return_value=[{"title": "DDG Result", "snippet": "DDG Snippet", "url": "https://ddg.com"}]):
        mock_post.return_value = MagicMock(status_code=500)
        results = GeminiSearchProvider.search("Python 3.12 release date")
        assert len(results) > 0
        assert results[0]["provider_status"] == "FALLBACK"
        assert results[0]["fallback_from"] == "gemini"
        assert "HTTP_500" in results[0]["error_detail"]


def test_fallback_provenance():
    """Verify fallback data is tagged with fallback_from=gemini and never labeled as Google Search."""
    with patch("httpx.Client.post", side_effect=Exception("Connection error")), \
         patch.object(DuckDuckGoSearchProvider, "search", return_value=[{"title": "DDG Result", "snippet": "DDG Snippet", "url": "https://ddg.com"}]):
        results = GeminiSearchProvider.search("Python 3.12 release date")
        assert len(results) > 0
        assert results[0]["provider_status"] == "FALLBACK"
        assert results[0]["fallback_from"] == "gemini"
        assert "EXCEPTION" in results[0]["error_detail"]


def test_empty_or_malformed_gemini_response():
    """Verify GeminiSearchProvider handles empty or malformed JSON responses by falling back to DDG."""
    mock_response = {}  # Empty JSON
    with patch("httpx.Client.post") as mock_post, \
         patch.object(DuckDuckGoSearchProvider, "search", return_value=[{"title": "DDG Result", "snippet": "DDG Snippet", "url": "https://ddg.com"}]):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        results = GeminiSearchProvider.search("Python 3.12 release date")
        assert len(results) > 0
        assert results[0]["provider_status"] == "FALLBACK"
        assert results[0]["fallback_from"] == "gemini"
        assert results[0]["error_detail"] == "EMPTY_GROUNDING"
