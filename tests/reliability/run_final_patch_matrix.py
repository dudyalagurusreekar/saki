"""
Final Patch Manual Test Matrix Runner
Evaluates all 10 queries to record:
- Runtime Date Authority
- Temporal Requirement & Classification
- Normal Saki Result vs Final Gemini Escalation
- Temporal Consistency Verification (Zero claims that 2026 is future or 2023 is current)
"""

import sys
import json
import time
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.services.action_engine import parse_query_understanding, decide_action, get_runtime_date_str, get_runtime_year
from backend.services.gemini_escalation import GeminiEscalationEngine
from backend.routes.chat import ChatRequest, chat

MATRIX_QUERIES = [
    {"id": 1, "query": "what is FastAPI"},
    {"id": 2, "query": "latest FastAPI version"},
    {"id": 3, "query": "latest Python version"},
    {"id": 4, "query": "best movies available in 2026"},
    {"id": 5, "query": "movies in 2025"},
    {"id": 6, "query": "movies in 2027"},
    {"id": 7, "query": "what happened in AI today"},
    {"id": 8, "query": "special food in Karnataka"},
    {"id": 9, "query": "special food in Vijayawada"},
    {"id": 10, "query": "Vijayawada history about temples"}
]


def run_patch_matrix():
    runtime_date = get_runtime_date_str()
    runtime_year = get_runtime_year()

    print("\n" + "=" * 95)
    print(f"FINAL PATCH: CURRENT-DATE SANITY & ESCALATION MATRIX (RUNTIME: {runtime_date})")
    print("=" * 95 + "\n")

    results = []

    for item in MATRIX_QUERIES:
        q_id = item["id"]
        query = item["query"]
        t0 = time.time()

        qu = parse_query_understanding(query)
        decision = decide_action(query)

        req = ChatRequest(message=query, conversation_id=f"patch-matrix-{q_id}-{int(time.time())}")
        chat_res = chat(req)
        elapsed_ms = round((time.time() - t0) * 1000, 2)

        final_text = chat_res.response

        # Check temporal consistency
        is_temp_valid, temp_reason = GeminiEscalationEngine.validate_temporal_consistency(
            draft_text=final_text,
            user_query=query,
            runtime_year=runtime_year
        )

        is_refusal = GeminiEscalationEngine.is_canned_refusal(final_text)
        escalation_occurred = is_refusal and decision.requires_world_access

        record = {
            "query_id": q_id,
            "query": query,
            "runtime_date": runtime_date,
            "temporal_requirement": decision.freshness_requirement,
            "normal_pipeline": "WEB" if decision.requires_world_access else "STATIC",
            "normal_pipeline_result": "ANSWERED" if not is_refusal else "CANNOT_ANSWER",
            "final_escalation": escalation_occurred,
            "gemini_called": escalation_occurred,
            "gemini_response": final_text if escalation_occurred else "N/A",
            "final_response": final_text[:140] + "..." if len(final_text) > 140 else final_text,
            "temporal_consistency": "VALID" if is_temp_valid else temp_reason,
            "latency_ms": elapsed_ms,
            "status": "PASS" if is_temp_valid else "FAIL"
        }
        results.append(record)

        print(f"Query {q_id}/10: \"{query}\"")
        print(f"  • Temporal Req: {decision.freshness_requirement} | Pipeline: {record['normal_pipeline']}")
        print(f"  • Saki Result: {record['normal_pipeline_result']} | Escalation: {record['final_escalation']}")
        print(f"  • Final Answer: \"{record['final_response'][:90]}...\"")
        print(f"  • Temporal Consistency: {record['temporal_consistency']} ({elapsed_ms}ms)\n")

    with open("tests/reliability/final_patch_matrix_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("=" * 95)
    print("PATCH MATRIX COMPLETE: ALL 10 QUERIES RECORDED")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    run_patch_matrix()
