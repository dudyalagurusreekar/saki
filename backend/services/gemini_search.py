"""
Saki Gemini Search Provider (External Intelligence & Web Grounding)
Executes real-time web retrieval via Gemini with Google Search tool grounding.
Extracts grounded text, Google web search queries, grounding chunks (URIs/titles),
and grounding support citations with automated fallback to DuckDuckGo.
"""

import time
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx

from backend.core.config import settings
from backend.services.world_access_manager import DuckDuckGoSearchProvider


GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiSearchProvider:
    """
    Controlled External Intelligence Provider using Gemini + Google Search Grounding.
    Provides verified real-time web search and evidence retrieval for Saki's brain.
    """

    @classmethod
    def search(cls, query: str, max_results: int = 5, timeout: float = 20.0) -> List[Dict[str, Any]]:
        """
        Executes Google Search grounding query via Gemini API and returns normalized search result items.
        Falls back to DuckDuckGoSearchProvider if Gemini API is unreachable, disabled, or unconfigured.
        """
        if not query or len(query.strip()) == 0:
            return []

        # Check configuration
        api_key = settings.GEMINI_API_KEY
        if not settings.ENABLE_GEMINI_SEARCH or not api_key or api_key == "your_gemini_api_key_here":
            results = DuckDuckGoSearchProvider.search(query, max_results=max_results)
            for item in results:
                item["fallback_from"] = "gemini"
                item["provider_status"] = "FALLBACK"
                item["error_detail"] = "DISABLED"
            return results

        try:
            model_name = getattr(settings, "GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
            url = f"{GEMINI_API_ENDPOINT.format(model=model_name)}?key={api_key}"

            # Task-oriented instruction for Gemini Google Search grounding
            task_prompt = (
                f"TASK:\n"
                f"Retrieve and extract the factual information required to answer the user's question.\n\n"
                f"USER QUESTION:\n"
                f"{query}\n\n"
                f"REQUIRED INFORMATION:\n"
                f"- Exact entity identification and details\n"
                f"- Core facts, dates, or figures requested\n"
                f"- Supporting source facts\n\n"
                f"DO NOT:\n"
                f"- Answer with conversational filler or unrelated details\n"
                f"- Invent missing information or speculate\n"
                f"- Make unsupported assumptions\n\n"
                f"RETURN:\n"
                f"A clean, factual summary containing the requested information and source URLs."
            )

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": task_prompt}]
                    }
                ],
                "tools": [
                    {"google_search": {}}
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1024
                }
            }

            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)

            if response.status_code != 200:
                results = DuckDuckGoSearchProvider.search(query, max_results=max_results)
                for item in results:
                    item["fallback_from"] = "gemini"
                    item["provider_status"] = "FALLBACK"
                    item["error_detail"] = f"HTTP_{response.status_code}"
                return results

            data = response.json()
            results = cls._parse_grounding_response(data, query, max_results)

            if results:
                for item in results:
                    item["provider_status"] = "SUCCESS"
                return results

            # If Gemini returned no grounding chunks/text, fallback to DuckDuckGo
            results = DuckDuckGoSearchProvider.search(query, max_results=max_results)
            for item in results:
                item["fallback_from"] = "gemini"
                item["provider_status"] = "FALLBACK"
                item["error_detail"] = "EMPTY_GROUNDING"
            return results

        except Exception as e:
            results = DuckDuckGoSearchProvider.search(query, max_results=max_results)
            for item in results:
                item["fallback_from"] = "gemini"
                item["provider_status"] = "FALLBACK"
                item["error_detail"] = f"EXCEPTION_{type(e).__name__}"
            return results

    @classmethod
    def _parse_grounding_response(cls, data: Dict[str, Any], query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Extracts structured search result dictionaries from Gemini generateContent JSON response.
        """
        candidates = data.get("candidates", [])
        if not candidates:
            return []

        cand = candidates[0]
        content_obj = cand.get("content", {})
        parts = content_obj.get("parts", [])
        grounded_text = "".join(p.get("text", "") for p in parts).strip()

        grounding_meta = cand.get("groundingMetadata", {})
        web_queries = grounding_meta.get("webSearchQueries", [query])
        grounding_chunks = grounding_meta.get("groundingChunks", [])
        grounding_supports = grounding_meta.get("groundingSupports", [])

        # Build support text mapping for chunk indices if available
        chunk_snippets: Dict[int, List[str]] = {}
        for supp in grounding_supports:
            segment_text = supp.get("segment", {}).get("text", "")
            indices = supp.get("groundingChunkIndices", [])
            for idx in indices:
                chunk_snippets.setdefault(idx, []).append(segment_text)

        results: List[Dict[str, Any]] = []
        seen_urls = set()

        for idx, chunk in enumerate(grounding_chunks):
            web_info = chunk.get("web", {})
            raw_url = web_info.get("uri", "")
            title = web_info.get("title", "").strip() or "Google Grounded Source"

            if not raw_url or raw_url in seen_urls:
                continue
            seen_urls.add(raw_url)

            # Determine snippet from grounded supports or grounded text summary
            supported_texts = chunk_snippets.get(idx, [])
            if supported_texts:
                snippet = " ".join(supported_texts).strip()
            elif grounded_text:
                snippet = grounded_text[:300]
            else:
                snippet = f"Verified public web information for '{query}' from {title}."

            parsed_url = urllib.parse.urlparse(raw_url)
            domain = parsed_url.netloc if parsed_url.netloc else "google.com"

            results.append({
                "title": title,
                "snippet": snippet,
                "url": raw_url,
                "domain": domain,
                "provider": "Google Search (Gemini Grounded)",
                "grounded_summary": grounded_text,
                "web_search_queries": web_queries,
                "retrieved_at": time.time()
            })

            if len(results) >= max_results:
                break

        # If no grounding chunks were returned but grounded_text exists, create an entry
        if not results and grounded_text:
            results.append({
                "title": f"Google Real-Time Intelligence for '{query}'",
                "snippet": grounded_text,
                "url": f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}",
                "domain": "google.com",
                "provider": "Google Search (Gemini Grounded)",
                "grounded_summary": grounded_text,
                "web_search_queries": web_queries,
                "retrieved_at": time.time()
            })

        return results

    @classmethod
    def search_grounded(cls, query: str, max_results: int = 5, timeout: float = 20.0) -> Dict[str, Any]:
        """
        Returns full structured grounded intelligence package including complete grounded synthesis,
        web search queries, and individual source items.
        """
        items = cls.search(query, max_results=max_results, timeout=timeout)
        grounded_summary = ""
        web_queries = [query]
        
        status = "SUCCESS"
        provider = "Google Search (Gemini Grounded)"
        fallback_from = None
        error_detail = None
        
        if items:
            grounded_summary = items[0].get("grounded_summary", items[0].get("snippet", ""))
            web_queries = items[0].get("web_search_queries", [query])
            provider = items[0].get("provider", provider)
            fallback_from = items[0].get("fallback_from")
            status = items[0].get("provider_status", "SUCCESS")
            error_detail = items[0].get("error_detail")
        else:
            status = "FAILED"
            error_detail = "NO_RESULTS"
            
        return {
            "query": query,
            "grounded_summary": grounded_summary,
            "web_search_queries": web_queries,
            "sources": items,
            "source_count": len(items),
            "provider": provider,
            "status": status,
            "fallback_from": fallback_from,
            "error_detail": error_detail
        }
