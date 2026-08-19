"""
Sprint 1 Manual Verification Matrix Runner
Executes the 10 representative queries defined in Part 13 and captures:
- QUERY
- WEB REQUIRED
- WEB EXECUTED
- PROVIDER
- QUERIES
- RESULT COUNT
- DUPLICATE PIPELINE
- FINAL RESPONSE
- PASS/PARTIAL/FAIL
"""

import os
import json
import time
from backend.models.schemas import ChatRequest
from backend.routes.chat import _execute_chat_pipeline
from backend.services.ai_service import call_model
from backend.services.response_evaluator import evaluate_response
from backend.services.web_controller import WebIntelligenceController
from backend.core.config import settings

MANUAL_QUERIES = [
    ("special food in Vijayawada", True, "Local food recommendations in Vijayawada"),
    ("good movies in 2026", True, "Current year (2026) movie recommendations"),
    ("latest Python version", True, "Current software version query"),
    ("latest FastAPI version", True, "Current software version query"),
    ("what happened in AI today", True, "Time-sensitive today news query"),
    ("best places to visit in Vijayawada", True, "Local tourism recommendations"),
    ("what is FastAPI", False, "Static conceptual definition"),
    ("explain overfitting", False, "Static machine learning concept"),
    ("how are you Saki", False, "Casual conversational banter"),
    ("tell me about an obscure local place", True, "Obscure local place inquiry requiring grounding")
]

def run_matrix():
    results = []
    print("\n" + "=" * 80)
    print("RUNNING SPRINT 1 MANUAL VERIFICATION MATRIX (10 QUERIES)")
    print("=" * 80 + "\n")

    for idx, (query, expected_web_req, description) in enumerate(MANUAL_QUERIES, start=1):
        print(f"[{idx}/10] Testing: '{query}' ({description})")
        req = ChatRequest(message=query, conversation_id=f"sprint1-matrix-{idx}")
        
        t0 = time.time()
        p = _execute_chat_pipeline(req)
        
        # Execute model response
        response = call_model(
            p.prompt,
            model=p.selected_model,
            keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
            images=p.image_paths if p.image_paths else None
        )
        latency = time.time() - t0
        
        eval_res = evaluate_response(response, plan=p.plan, mode=p.decision.conversation_mode)
        final_resp = eval_res.repaired_text

        # Extract diagnostics
        action_decision = p.decision.action_decision
        web_required = action_decision.requires_world_access if action_decision else False
        
        last_trace = getattr(WebIntelligenceController, "_last_diagnostic_trace", {}) or {}
        provider = last_trace.get("SEARCH_PROVIDER", "None (No Web)") if web_required else "N/A (Local)"
        provider_status = last_trace.get("PROVIDER_STATUS", "SKIPPED") if web_required else "SKIPPED"
        queries_exec = last_trace.get("QUERIES_EXECUTED", []) if web_required else []
        result_count = len(p.evidence_items) if p.evidence_items else 0
        duplicate_pipeline = last_trace.get("DUPLICATE_PIPELINE", False)
        
        # Evaluation check
        web_match = (web_required == expected_web_req)
        no_dup = (duplicate_pipeline is False)
        
        if web_match and no_dup and eval_res.score >= 0.85:
            verdict = "PASS"
        elif web_match and no_dup:
            verdict = "PARTIAL"
        else:
            verdict = "FAIL"

        entry = {
            "id": idx,
            "query": query,
            "description": description,
            "web_required": web_required,
            "expected_web_required": expected_web_req,
            "web_executed": web_required and provider_status != "SKIPPED",
            "provider": provider,
            "provider_status": provider_status,
            "queries": queries_exec,
            "result_count": result_count,
            "duplicate_pipeline": duplicate_pipeline,
            "selected_model": p.selected_model,
            "final_response": final_resp[:300] + ("..." if len(final_resp) > 300 else ""),
            "eval_score": eval_res.score,
            "latency_s": round(latency, 2),
            "verdict": verdict
        }
        results.append(entry)
        print(f"      -> Web Required: {web_required} (Expected: {expected_web_req}) | Provider: {provider} | Verdict: {verdict}\n")

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reliability", "sprint1_matrix_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nMatrix results saved to: {output_path}")
    return results

if __name__ == "__main__":
    run_matrix()
