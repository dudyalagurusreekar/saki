"""
Sprint 6 Latency & Forensic Tracer for:
1. "Vijayawada history about temples" (Test A)
2. "latest FastAPI version" (Test B)

Measures stage-by-stage latencies:
- intent_decision_latency
- web_decision_latency
- provider_latency
- evidence_latency
- context_latency
- model_latency
- total_latency
And captures all 15 forensic checkpoints.
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

from backend.routes.chat import ChatRequest, _execute_chat_pipeline, call_model, evaluate_response
from backend.services.action_engine import parse_query_understanding, decide_action
from backend.services.web_controller import WebIntelligenceController
from backend.services.gemini_search import GeminiSearchProvider
from backend.core.config import settings

TARGET_QUERIES = [
    ("TEST A", "Vijayawada history about temples"),
    ("TEST B", "latest FastAPI version")
]


def trace_query(test_label: str, query: str):
    print("\n" + "=" * 80)
    print(f"TRACING {test_label}: '{query}'")
    print("=" * 80)

    t_start = time.time()

    # Stage 1: Query Understanding & Intent
    t0 = time.time()
    qu = parse_query_understanding(query)
    t_qu = time.time() - t0

    # Stage 2: Action Decision
    t0 = time.time()
    decision = decide_action(query)
    t_decision = time.time() - t0

    print(f"1. Query Understanding: entity='{qu.primary_entity}', topic='{qu.topic}', intent='{qu.intent}', temporal='{qu.temporal_requirement}' ({round(t_qu*1000, 2)}ms)")
    print(f"2. Action Decision: action='{decision.action}', requires_world_access={decision.requires_world_access}, freshness='{decision.freshness_requirement}' ({round(t_decision*1000, 2)}ms)")
    print(f"3. Optimized Search Query: '{qu.search_query_optimized}'")

    # Stage 3: Direct Gemini Provider Trace
    t_provider = 0.0
    gemini_results = []
    gemini_status = "SKIPPED"
    gemini_error = None

    if decision.requires_world_access:
        t0 = time.time()
        search_q = qu.search_query_optimized or query
        gemini_results = GeminiSearchProvider.search(search_q, max_results=4)
        t_provider = time.time() - t0
        if gemini_results:
            gemini_status = gemini_results[0].get("provider_status", "UNKNOWN")
            gemini_error = gemini_results[0].get("error_detail")
        print(f"4. Gemini Provider Call: status='{gemini_status}', error='{gemini_error}', count={len(gemini_results)} ({round(t_provider, 2)}s)")

    # Stage 4: Full Chat Pipeline Execution
    req = ChatRequest(
        message=query,
        conversation_id=f"sprint6-trace-{int(time.time())}"
    )

    t0 = time.time()
    pipeline_res = _execute_chat_pipeline(req)
    t_pipeline = time.time() - t0

    trace = WebIntelligenceController.get_last_diagnostic_trace() or {}
    evidence_count = len(pipeline_res.evidence_items or [])
    passed_to_model = bool(pipeline_res.evidence_package and pipeline_res.evidence_package.evidence_status == "SUFFICIENT")

    print(f"5. Pipeline Execution: selected_model='{pipeline_res.selected_model}', evidence_count={evidence_count}, passed_to_model={passed_to_model} ({round(t_pipeline, 2)}s)")

    # Stage 5: Final Model Call
    t0 = time.time()
    response = call_model(
        pipeline_res.prompt,
        model=pipeline_res.selected_model,
        keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
        images=pipeline_res.image_paths if pipeline_res.image_paths else None
    )
    t_model = time.time() - t0

    eval_res = evaluate_response(response, plan=pipeline_res.plan, mode=pipeline_res.decision.conversation_mode)
    final_text = eval_res.repaired_text

    t_total = time.time() - t_start

    print(f"6. Model Generation: model='{pipeline_res.selected_model}' ({round(t_model, 2)}s)")
    print(f"7. Final Total Latency: {round(t_total, 2)}s")
    print(f"8. Final Answer Snippet:\n   {final_text[:180]}...\n")

    return {
        "label": test_label,
        "query": query,
        "entity": qu.primary_entity,
        "topic": qu.topic,
        "intent": qu.intent,
        "temporal_requirement": qu.temporal_requirement,
        "web_required": decision.requires_world_access,
        "search_query": qu.search_query_optimized,
        "gemini_status": gemini_status,
        "gemini_error": gemini_error,
        "gemini_result_count": len(gemini_results),
        "evidence_count": evidence_count,
        "passed_to_model": passed_to_model,
        "selected_model": pipeline_res.selected_model,
        "final_answer": final_text,
        "latencies": {
            "query_understanding_ms": round(t_qu * 1000, 2),
            "decision_ms": round(t_decision * 1000, 2),
            "provider_s": round(t_provider, 2),
            "pipeline_s": round(t_pipeline, 2),
            "model_s": round(t_model, 2),
            "total_s": round(t_total, 2)
        }
    }


def run_traces():
    results = []
    for label, q in TARGET_QUERIES:
        res = trace_query(label, q)
        results.append(res)

    with open("tests/reliability/sprint6_trace_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("Saved trace output to tests/reliability/sprint6_trace_output.json")


if __name__ == "__main__":
    run_traces()
