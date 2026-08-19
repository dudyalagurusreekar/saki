"""
Diagnostic script to trace 'what current fastapi version' step-by-step through the entire pipeline.
"""
import sys
from backend.models.schemas import ChatRequest
from backend.services.action_engine import decide_action, classify_freshness
from backend.services.orchestrator import SakiModelOrchestrator
from backend.services.gemini_search import GeminiSearchProvider
from backend.services.web_controller import WebIntelligenceController
from backend.routes.chat import _execute_chat_pipeline
from backend.core.config import settings

def trace_query(query: str = "what current fastapi version"):
    print("=" * 80)
    print(f"TRACING QUERY: '{query}'")
    print("=" * 80)

    # 1. ActionEngine decision
    print("\n--- 1. Action Decision Engine ---")
    action_decision = decide_action(query)
    print(f"Action: {action_decision.action}")
    print(f"Requires World Access: {action_decision.requires_world_access}")
    print(f"Freshness Requirement: {action_decision.freshness_requirement}")
    print(f"Query Intent: {action_decision.query_intent}")
    print(f"Reason: {action_decision.reason}")

    # 2. Orchestrator routing
    print("\n--- 2. Orchestrator Routing ---")
    routing_decision = SakiModelOrchestrator.classify_request(query)
    print(f"Selected Model: {routing_decision.selected_model}")
    print(f"Task Type: {routing_decision.task_type}")
    print(f"Conversation Mode: {routing_decision.conversation_mode}")

    # 3. Gemini Search Provider Direct Call
    print("\n--- 3. Gemini Search Provider Direct Test ---")
    print(f"GEMINI_API_KEY present: {bool(settings.GEMINI_API_KEY)}")
    print(f"GEMINI_SEARCH_MODEL: {settings.GEMINI_SEARCH_MODEL}")
    try:
        raw_results = GeminiSearchProvider.search(query, max_results=4)
        print(f"GeminiSearchProvider returned {len(raw_results)} items.")
        for idx, item in enumerate(raw_results, 1):
            print(f"  Item {idx}: Title='{item.get('title')}', Provider='{item.get('provider')}', Status='{item.get('provider_status')}'")
            print(f"          URL='{item.get('url')}'")
            print(f"          Snippet='{item.get('snippet', '')[:120]}...'")
    except Exception as e:
        print(f"GeminiSearchProvider raised exception: {e}")

    # 4. Web Intelligence Controller Execution
    print("\n--- 4. WebIntelligenceController Execution ---")
    web_res = WebIntelligenceController.execute(query, action_decision)
    print(f"Web Required: {web_res.web_required}")
    print(f"Provider: {web_res.provider}")
    print(f"Provider Status: {web_res.provider_status}")
    print(f"Provider Call Count: {web_res.provider_call_count}")
    print(f"Queries Executed: {web_res.queries_executed}")
    print(f"Result Count: {web_res.result_count}")
    print(f"Evidence Items Count: {len(web_res.evidence_items)}")
    print(f"Has Evidence Package: {web_res.evidence_package is not None}")
    if web_res.evidence_package:
        print(f"Evidence Package Status: {web_res.evidence_package.evidence_status}")
        print(f"Evidence Package Claims Count: {len(web_res.evidence_package.claims)}")
        print(f"Evidence Package Sources Count: {len(web_res.evidence_package.sources)}")
    print(f"Grounded Prompt Block:\n{web_res.grounded_prompt_block}")

    # 5. Full Chat Pipeline Execution
    print("\n--- 5. Full Chat Pipeline Execution ---")
    req = ChatRequest(message=query, conversation_id="trace-fastapi-current")
    p = _execute_chat_pipeline(req)
    print(f"Selected Model for Inference: {p.selected_model}")
    print(f"Evidence Items in Pipeline: {len(p.evidence_items or [])}")
    print(f"Evidence Package in Pipeline: {p.evidence_package is not None}")
    print(f"Web Intel Res in Pipeline: {p.web_intel_res is not None}")
    print(f"\nFinal Prompt Received by Model:\n{'-'*40}\n{p.prompt}\n{'-'*40}")

if __name__ == "__main__":
    trace_query()
