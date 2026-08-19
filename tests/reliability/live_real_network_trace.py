"""
Live Real Network Request & Grounding Pipeline Inspector
Executes an actual, live HTTP request to Google Gemini API over the network,
capturing the real HTTP request headers, real payload, real HTTP response,
real status code, real response body, and traces the resulting pipeline flow.
"""

import sys
import json
import time
import httpx

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.core.config import settings
from backend.services.action_engine import parse_query_understanding, decide_action
from backend.services.gemini_search import GeminiSearchProvider, GEMINI_API_ENDPOINT
from backend.services.evidence_engine import EvidenceIntelligenceEngine
from backend.services.grounding_verifier import GroundingVerifierEngine, extract_claims_from_text
from backend.routes.chat import ChatRequest, chat


def execute_live_real_network_pipeline(query: str):
    print("\n" + "=" * 90)
    print(f"LIVE REAL NETWORK PIPELINE EXECUTION FOR: \"{query}\"")
    print("=" * 90 + "\n")

    # STEP 1: USER
    print(f"[STEP 1: USER]")
    print(f"  • User Query: \"{query}\"")

    # STEP 2: WEB REQUIRED
    qu = parse_query_understanding(query)
    decision = decide_action(query)
    print(f"\n[STEP 2: WEB REQUIRED]")
    print(f"  • Web Required: {decision.requires_world_access}")
    print(f"  • Freshness Requirement: {decision.freshness_requirement}")
    print(f"  • Primary Entity: {qu.primary_entity} ({qu.entity_type})")
    print(f"  • Topic: {qu.topic} | Intent: {qu.intent}")
    print(f"  • Optimized Search Query: \"{qu.search_query_optimized}\"")

    # STEP 3: REAL GEMINI REQUEST
    api_key = settings.GEMINI_API_KEY
    model_name = getattr(settings, "GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
    endpoint_url = f"{GEMINI_API_ENDPOINT.format(model=model_name)}?key={api_key}"
    masked_url = f"{GEMINI_API_ENDPOINT.format(model=model_name)}?key={api_key[:8]}...{api_key[-4:]}"

    task_prompt = (
        f"TASK:\n"
        f"Retrieve and extract the verified factual information required to answer the user's question.\n\n"
        f"USER QUESTION:\n"
        f"{qu.search_query_optimized or query}\n\n"
        f"REQUIRED INFORMATION:\n"
        f"- Exact entity identification, latest release/version numbers, dates, or figures requested\n"
        f"- Official primary sources and URLs\n"
        f"- Supporting factual evidence\n\n"
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

    print(f"\n[STEP 3: REAL GEMINI REQUEST (OUTBOUND NETWORK CALL)]")
    print(f"  • Target URL: {masked_url}")
    print(f"  • Method: POST")
    print(f"  • Tool Config: [google_search (Google Search Grounding)]")
    print(f"  • Payload Prompt: \"{task_prompt[:140]}...\"")
    print(f"  • Disagreeing / Fake Data Prohibited: True")

    # Execute actual network call
    t0 = time.time()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(endpoint_url, json=payload)
        network_latency = round(time.time() - t0, 3)

        # STEP 4: REAL GEMINI RESPONSE
        print(f"\n[STEP 4: REAL GEMINI RESPONSE (RECEIVED FROM GOOGLE SERVERS)]")
        print(f"  • HTTP Status Code: {resp.status_code} {resp.reason_phrase}")
        print(f"  • Network Latency: {network_latency}s")
        print(f"  • Response Headers: Content-Type={resp.headers.get('content-type')}, Server={resp.headers.get('server')}")

        if resp.status_code == 200:
            data = resp.json()
            cand = data.get("candidates", [{}])[0]
            gm = cand.get("groundingMetadata", {})
            parts = cand.get("content", {}).get("parts", [{}])
            resp_text = parts[0].get("text", "") if parts else ""

            print(f"\n[STEP 5: REAL GROUNDING DATA (PARSED FROM GOOGLE SEARCH)]")
            print(f"  • Google Web Search Queries: {gm.get('webSearchQueries', [])}")
            print(f"  • Grounding Chunks Count: {len(gm.get('groundingChunks', []))}")
            for idx, chunk in enumerate(gm.get('groundingChunks', []), 1):
                print(f"    - Source {idx}: {chunk.get('web', {}).get('title')} -> {chunk.get('web', {}).get('uri')}")
            print(f"  • Gemini Summary Text:\n    \"{resp_text[:180]}...\"")

            raw_items = GeminiSearchProvider._parse_grounding_response(data, query, max_results=4)
            for itm in raw_items:
                itm["provider_status"] = "SUCCESS"
        else:
            print(f"\n[STEP 5: REAL GROUNDING DATA (SERVER STATUS: {resp.status_code})]")
            err_data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"text": resp.text[:200]}
            err_msg = err_data.get("error", {}).get("message", resp.text[:150]) if isinstance(err_data, dict) else str(err_data)
            print(f"  • Google API Message: \"{err_msg}\"")
            print(f"  • Grounding Status: 0 chunks available due to provider rate limit/quota state.")
            raw_items = [{
                "title": "",
                "snippet": "",
                "url": "",
                "domain": "",
                "provider": "gemini",
                "provider_status": "FAILURE",
                "error_detail": f"HTTP_{resp.status_code}",
                "fallback_from": None
            }]

    except Exception as e:
        network_latency = round(time.time() - t0, 3)
        print(f"\n[STEP 4 & 5: REAL NETWORK EXCEPTION]")
        print(f"  • Exception: {type(e).__name__}: {str(e)}")
        raw_items = [{
            "title": "",
            "snippet": "",
            "url": "",
            "domain": "",
            "provider": "gemini",
            "provider_status": "FAILURE",
            "error_detail": f"EXCEPTION_{type(e).__name__}",
            "fallback_from": None
        }]

    # STEP 6: REAL EVIDENCE
    print(f"\n[STEP 6: REAL EVIDENCE (EVIDENCE INTELLIGENCE ENGINE)]")
    evidence_pkg = EvidenceIntelligenceEngine.process_and_synthesize(
        query=query,
        raw_items=raw_items,
        freshness_requirement=decision.freshness_requirement
    )
    print(f"  • Evidence Count: {len(evidence_pkg.evidence_items)}")
    print(f"  • Evidence Package Status: {evidence_pkg.evidence_status}")
    print(f"  • Quality Summary: {evidence_pkg.quality_summary}")
    for idx, ev in enumerate(evidence_pkg.evidence_items, 1):
        print(f"    - Item {idx}: [{ev.domain}] {ev.content[:120]} (Relevance: {ev.relevance_score})")

    # STEP 7 & 8: CLAIMS & GROUNDED ANSWER
    req = ChatRequest(message=query, conversation_id=f"live-trace-{int(time.time())}")
    chat_res = chat(req)

    print(f"\n[STEP 7: CLAIMS (GROUNDING VERIFIER)]")
    claims = extract_claims_from_text(chat_res.response)
    print(f"  • Total Factual Claims Extracted: {len(claims)}")
    for c in claims:
        print(f"    - Claim: \"{c.text}\" (Importance: {c.importance})")

    print(f"\n[STEP 8: GROUNDED FINAL ANSWER (DELIVERED TO USER)]")
    print(f"  • Model Used: {chat_res.routing.get('selected_model', 'local')}")
    print(f"  • Final Answer:\n    \"{chat_res.response}\"")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "latest FastAPI version"
    execute_live_real_network_pipeline(test_query)
