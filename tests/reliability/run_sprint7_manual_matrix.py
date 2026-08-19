"""
Sprint 7 Manual Test Matrix Runner (Part 19)
Executes 8 target queries across the full chat pipeline with Claim-Level Grounding & Verification:
1. latest FastAPI version
2. special food in Vijayawada
3. Vijayawada history about temples
4. what is FastAPI
5. good movies in 2026
6. latest Python version
7. tell me about an obscure local temple
8. tell me something about Vijayawada

Records for each query:
- Query
- Factual claims extracted
- Evidence items & supporting claims
- Unsupported claims detected
- Contradictions detected
- Grounding status & source mode
- Final answer after grounding repair
"""

import sys
import json
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.routes.chat import ChatRequest, chat, _execute_chat_pipeline, call_model
from backend.services.response_evaluator import evaluate_response
from backend.services.grounding_verifier import GroundingVerifierEngine
from backend.core.config import settings

MATRIX_QUERIES = [
    "latest FastAPI version",
    "special food in Vijayawada",
    "Vijayawada history about temples",
    "what is FastAPI",
    "good movies in 2026",
    "latest Python version",
    "tell me about an obscure local temple",
    "tell me something about Vijayawada"
]


def run_matrix():
    results = []
    print("\n" + "=" * 80)
    print("SAKI SPRINT 7: CLAIM-LEVEL GROUNDING & ANSWER VERIFICATION MATRIX")
    print("=" * 80 + "\n")

    for idx, query in enumerate(MATRIX_QUERIES, 1):
        print(f"[{idx}/{len(MATRIX_QUERIES)}] Evaluating Query: '{query}'...")
        req = ChatRequest(
            message=query,
            conversation_id=f"sprint7-manual-{idx}-{int(time.time())}"
        )

        t0 = time.time()
        p = _execute_chat_pipeline(req)
        t_pipeline = time.time() - t0

        t0 = time.time()
        draft_response = call_model(
            p.prompt,
            model=p.selected_model,
            keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
            images=p.image_paths if p.image_paths else None
        )
        t_model = time.time() - t0

        t0 = time.time()
        eval_res = evaluate_response(
            draft_response,
            plan=p.plan,
            mode=p.decision.conversation_mode,
            evidence_items=p.evidence_items,
            evidence_package=p.evidence_package,
            action_decision=p.decision.action_decision if p.decision else None,
            user_query=p.user_input
        )
        t_eval = time.time() - t0

        assessment = eval_res.grounding_assessment

        claims_data = []
        if assessment:
            for c in assessment.claims:
                claims_data.append({
                    "id": c.claim_id,
                    "text": c.text,
                    "importance": c.importance,
                    "support_status": c.support_status,
                    "directness": c.directness,
                    "confidence": c.confidence,
                    "reason": c.reason
                })

        entry = {
            "query_id": idx,
            "query": query,
            "selected_model": p.selected_model,
            "grounding_status": assessment.grounding_status if assessment else "STATIC",
            "source_mode": assessment.answer_source_mode if assessment else "STATIC_KNOWLEDGE",
            "total_claims": assessment.total_claims if assessment else 0,
            "supported_claims": assessment.supported_claims if assessment else 0,
            "unsupported_claims": assessment.unsupported_claims if assessment else 0,
            "contradicted_claims": assessment.contradicted_claims if assessment else 0,
            "critical_claims_supported": assessment.critical_claims_supported if assessment else True,
            "draft_answer": draft_response.strip(),
            "final_answer": eval_res.repaired_text.strip(),
            "claims": claims_data,
            "evidence_count": len(p.evidence_items or []),
            "latencies": {
                "pipeline_s": round(t_pipeline, 2),
                "model_generation_s": round(t_model, 2),
                "grounding_eval_ms": round(t_eval * 1000, 2),
                "total_s": round(t_pipeline + t_model + t_eval, 2)
            }
        }
        results.append(entry)

        print(f"  Source Mode: {entry['source_mode']} | Status: {entry['grounding_status']}")
        print(f"  Claims: total={entry['total_claims']}, supported={entry['supported_claims']}, unsupported={entry['unsupported_claims']}")
        print(f"  Final Answer: {entry['final_answer'][:140]}...")
        print(f"  Grounding Latency: {entry['latencies']['grounding_eval_ms']}ms | Total: {entry['latencies']['total_s']}s\n")

    with open("tests/reliability/sprint7_matrix_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("Saved matrix output to tests/reliability/sprint7_matrix_output.json")
    return results


if __name__ == "__main__":
    run_matrix()
