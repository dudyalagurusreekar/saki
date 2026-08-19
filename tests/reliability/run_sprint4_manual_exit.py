"""
Sprint 4 Manual Exit Test Runner
Executes queries A-H specified in Part 16 and captures full responses.
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

EXIT_QUERIES = [
    ("A", "latest FastAPI version", True, "Current software version query"),
    ("B", "current FastAPI version", True, "Current software version query"),
    ("C", "latest Python version", True, "Current software version query"),
    ("D", "latest Node.js version", True, "Current software version query"),
    ("E", "what happened in AI today", True, "Time-sensitive today news query"),
    ("F", "good movies in 2026", True, "Current year (2026) recommendation query"),
    ("G", "special food in Vijayawada", True, "Local culinary recommendation query"),
    ("H", "what is FastAPI", False, "Static general knowledge query")
]

def run_exit_tests():
    print("=" * 80)
    print("RUNNING SPRINT 4 MANUAL EXIT TESTS (QUERIES A-H)")
    print("=" * 80 + "\n")

    results = []
    for label, query, expected_web_req, desc in EXIT_QUERIES:
        print(f"[{label}] Query: '{query}' ({desc})")
        req = ChatRequest(message=query, conversation_id=f"sprint4-exit-{label}")
        
        t0 = time.time()
        p = _execute_chat_pipeline(req)
        response = call_model(
            p.prompt,
            model=p.selected_model,
            keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
            images=p.image_paths if p.image_paths else None
        )
        latency = time.time() - t0
        eval_res = evaluate_response(response, plan=p.plan, mode=p.decision.conversation_mode)
        final_text = eval_res.repaired_text

        action_decision = p.decision.action_decision
        web_req = action_decision.requires_world_access if action_decision else False
        temporal_req = getattr(action_decision, "temporal_requirement", "STABLE") if action_decision else "STABLE"
        
        last_trace = getattr(WebIntelligenceController, "_last_diagnostic_trace", {}) or {}
        provider = last_trace.get("provider", "N/A (Local)") if web_req else "N/A (Local)"
        provider_status = last_trace.get("provider_status", "SKIPPED") if web_req else "SKIPPED"
        ev_count = len(p.evidence_items) if p.evidence_items else 0
        ev_passed = last_trace.get("evidence_passed_to_model", False) if web_req else False

        entry = {
            "label": label,
            "query": query,
            "description": desc,
            "web_required": web_req,
            "temporal_requirement": temporal_req,
            "provider": provider,
            "provider_status": provider_status,
            "evidence_count": ev_count,
            "evidence_passed_to_model": ev_passed,
            "selected_model": p.selected_model,
            "final_answer": final_text,
            "latency_s": round(latency, 2)
        }
        results.append(entry)

        safe_ans = final_text.encode("ascii", "replace").decode("ascii")[:100]
        print(f"    -> Web Req: {web_req} | Temporal: {temporal_req} | Provider: {provider} ({provider_status})")
        print(f"    -> Response: {safe_ans}...\n")

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reliability", "sprint4_exit_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Exit test results saved to: {output_path}")
    return results

if __name__ == "__main__":
    run_exit_tests()
