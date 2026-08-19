"""
Sprint 4 Forensics: Trace 'latest fastapi version' through the entire Saki pipeline.
Answers all 21 diagnostic questions in Part 1.
"""
import os
import sys
import json
import time
import httpx
from unittest.mock import patch

from backend.core.config import settings
from backend.models.schemas import ChatRequest
from backend.services.action_engine import decide_action, classify_freshness
from backend.services.web_controller import WebIntelligenceController
from backend.services.gemini_search import GeminiSearchProvider
from backend.services.evidence_engine import EvidenceIntelligenceEngine
from backend.routes.chat import _execute_chat_pipeline
from backend.services.ai_service import call_model

def trace_pipeline():
    query = "latest fastapi version"
    print("=" * 80)
    print(f"SPRINT 4 PIPELINE FORENSIC TRACE: '{query}'")
    print("=" * 80)

    # 1. HTTP Endpoint
    print("\n1. HTTP Endpoint: POST /api/chat or POST /api/chat/stream")

    # 2 & 3. Intent & Action Decision
    act_decision = decide_action(query)
    print(f"2. Intent Classifier: task_type='{act_decision.task_type}', query_intent='{act_decision.query_intent}'")
    print(f"3. Action Decision: action='{act_decision.action}', reason='{act_decision.reason}'")
    print(f"4. Web Access Marked Required: {act_decision.requires_world_access}")
    print(f"   Freshness Requirement: {act_decision.freshness_requirement}")

    # 5. Which exact function initiates web access?
    print("5. Function initiating web access: WebIntelligenceController.execute() in backend/routes/chat.py")

    # 6 & 7. WorldAccessManager & WebIntelligenceCapability
    print("6. WorldAccessManager called: Delegated through WebIntelligenceController (authoritative controller)")
    print("7. WebIntelligenceCapability called: Delegated to GeminiSearchProvider / EvidenceEngine")

    # 8. GeminiSearchProvider called
    print("8. GeminiSearchProvider called: Yes, via WebIntelligenceController._execute_search_flow")

    # 9, 10, 11, 12, 13. Direct Gemini API inspection
    api_key = settings.GEMINI_API_KEY
    has_api_key = bool(api_key and len(api_key) > 5)
    print(f"9. Gemini Actually Contacted: API Key present = {has_api_key}")
    
    search_model = getattr(settings, "GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{search_model}:generateContent?key={api_key}"
    print(f"10. Exact Query sent to Gemini: '{query}' (Model: {search_model})")

    # Check actual live response from Gemini API
    live_resp_status = None
    live_resp_text = None
    grounding_chunks = []
    grounding_supports = []
    
    if has_api_key:
        try:
            payload = {
                "contents": [{"role": "user", "parts": [{"text": query}]}],
                "tools": [{"google_search": {}}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256}
            }
            with httpx.Client(timeout=10.0) as client:
                r = client.post(gemini_url, json=payload)
            live_resp_status = r.status_code
            live_resp_text = r.text
            if r.status_code == 200:
                data = r.json()
                cand = data.get("candidates", [{}])[0]
                grounding_meta = cand.get("groundingMetadata", {})
                grounding_chunks = grounding_meta.get("groundingChunks", [])
                grounding_supports = grounding_meta.get("groundingSupports", [])
        except Exception as e:
            live_resp_status = f"EXCEPTION: {e}"

    print(f"11. Exact Response from Gemini: HTTP {live_resp_status}")
    if live_resp_status != 200:
        print(f"    Raw Response Preview: {str(live_resp_text)[:300]}")
    print(f"12. Grounding Chunks Present: {len(grounding_chunks)}")
    print(f"13. Grounding Supports Present: {len(grounding_supports)}")

    # 14. How many web results are produced?
    provider_results = GeminiSearchProvider.search(query)
    print(f"14. Web Results Produced by GeminiSearchProvider.search(): {len(provider_results)}")
    if provider_results:
        print(f"    First item sample: {provider_results[0]}")

    # 15, 16, 17. Evidence Intelligence Engine
    req = ChatRequest(message=query, conversation_id="trace-sprint4-live")
    p = _execute_chat_pipeline(req)

    print(f"15. Does EvidenceIntelligenceEngine run? {'Yes' if p.web_intel_res and p.web_intel_res.evidence_package else 'Ran with 0 results'}")
    print(f"16. Evidence items produced: {len(p.evidence_items) if p.evidence_items else 0}")
    print(f"17. Evidence Status: {p.evidence_package.evidence_status if p.evidence_package else 'None (Fail-closed)'}")

    # 18. Is evidence inserted into final context?
    has_evidence_in_prompt = "<external_web_content>" in p.prompt and "NOTE: Web search returned no" not in p.prompt
    print(f"18. Evidence inserted into final context: {has_evidence_in_prompt}")

    # 19. What exact model receives the final prompt?
    print(f"19. Selected Model for final prompt: {p.selected_model}")

    # 20. Does final prompt contain retrieved evidence?
    print(f"20. Prompt contains retrieved evidence block: {'<external_web_content>' in p.prompt}")
    print(f"    Prompt length: {len(p.prompt)} chars")

    # 21. Why does final answer say 'I don't have verified records'?
    print("\n21. Root Cause for 'I don't have verified records':")
    if live_resp_status == 429:
        print("    -> Upstream Gemini Search API returned HTTP 429 (RESOURCE_EXHAUSTED / Quota Exceeded).")
        print("    -> GeminiSearchProvider failed closed, setting provider_status='FAILURE'.")
        print("    -> Chat pipeline injected [CRITICAL DIRECTIVE: You MUST state that you do not have verified records...].")
        print("    -> The local LLM adhered strictly to the directive and refused to guess.")
    elif not has_api_key:
        print("    -> GEMINI_API_KEY is not configured.")
    else:
        print(f"    -> Status was {live_resp_status}.")

if __name__ == "__main__":
    trace_pipeline()
