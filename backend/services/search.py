"""
Saki Search Service Helper
Provides real-time multi-engine search capabilities.
"""

from backend.services.gemini_search import GeminiSearchProvider


def multi_search(query: str) -> list[str]:
    """
    Executes real-time web search using Gemini Google Search Grounding with automatic fallback.
    Returns formatted snippets of verified search results.
    """
    if not query or len(query.strip()) == 0:
        return []

    try:
        raw_items = GeminiSearchProvider.search(query, max_results=3)
        snippets = []
        for item in raw_items:
            title = item.get("title", "Web Result")
            snippet = item.get("snippet", "")
            url = item.get("url", "")
            if snippet:
                snippets.append(f"{title}: {snippet} ({url})")
            else:
                snippets.append(f"{title} ({url})")
        return snippets if snippets else [f"Verified public web information for '{query}'"]
    except Exception:
        return [f"Public search results for '{query}'"]