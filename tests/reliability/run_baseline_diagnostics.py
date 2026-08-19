"""
Sprint 0 Diagnostic Test Execution Script
Runs diagnostic queries through Saki's live backend pipeline, capturing
empirical telemetry across all 16 pipeline stages without modifying system behavior.
"""

import sys
import os
import time
import json

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.models.schemas import ChatRequest
from backend.routes.chat import _execute_chat_pipeline, evaluate_response
from backend.services.ai_service import call_model, stream_model
from backend.core.config import settings
from backend.services.memory_service import load_memory, save_memory, invalidate_memory_cache

CATEGORIES = {
    "A": [
        "Hey Saki",
        "How are you?",
        "Tell me something interesting.",
        "Good morning Saki."
    ],
    "B": [
        "What is FastAPI?",
        "What is overfitting?",
        "Explain transformers in machine learning.",
        "What is the difference between RAM and VRAM?"
    ],
    "C": [
        "What is the latest Python version?",
        "What is the latest version of FastAPI?",
        "What are the latest developments in AI?",
        "What is happening in technology right now?"
    ],
    "D": [
        "What is special about Kambadur Temple in Andhra Pradesh?",
        "Who built Kambadur Temple?",
        "What are special places in Vijayawada?",
        "Tell me about Lepakshi Temple in Andhra Pradesh."
    ],
    "E": [
        "Tell me about XYZ12345 Temple in Andhra Pradesh.",
        "Who built the ancient fort of FooBarBaz in 1421?",
        "What is special about the village of QuxQuuxZapr in India?"
    ],
    "F": [
        "Tell me about Saki.",
        "Tell me about Python.",
        "Tell me about Gemini."
    ],
    "G": [
        "My favorite test project is Project Aurora.",
        "What is my favorite test project?"
    ],
    "H": [
        "I am currently working on Project Aurora.",
        "What project am I working on?",
        "What were we working on?"
    ],
    "I": [
        "We decided to use Gemini for web grounding in Project Aurora.",
        "What did we decide for web grounding?"
    ],
    "J": [
        "Does the government support heritage maintenance for Kambadur Temple?"
    ],
    "K": [
        "Explain this Python error: NameError: name 'x' is not defined",
        "Write a Python function to reverse a string.",
        "Why does this code fail: def add(a, b): return a + c"
    ],
    "L": [
        "I'm frustrated because my project isn't working."
    ]
}

STREAMING_COMPARISON_QUERIES = [
    "Hey Saki",
    "What is FastAPI?",
    "What is the latest Python version?",
    "What is special about Kambadur Temple in Andhra Pradesh?",
    "Write a Python function to reverse a string."
]


def run_diagnostics():
    print("==================================================")
    print("STARTING SPRINT 0 DIAGNOSTIC TEST RUNNER")
    print("==================================================")

    results = []

    for cat, queries in CATEGORIES.items():
        print(f"\n--- Running Category {cat} ---")
        for q in queries:
            start_t = time.time()
            req = ChatRequest(message=q, conversation_id="sprint0-diag-session")
            
            try:
                pipeline_res = _execute_chat_pipeline(req)
                
                # Model execution
                response_text = call_model(
                    pipeline_res.prompt,
                    model=pipeline_res.selected_model,
                    keep_alive=settings.MODEL_KEEP_ALIVE_SESSION
                )
                
                eval_res = evaluate_response(
                    response_text,
                    plan=pipeline_res.plan,
                    mode=pipeline_res.decision.conversation_mode
                )
                
                elapsed = time.time() - start_t
                
                action_dec = pipeline_res.decision.action_decision
                action_name = action_dec.action if action_dec else "NONE"
                req_world = action_dec.requires_world_access if action_dec else False
                
                ev_pkg = pipeline_res.evidence_package
                ev_status = ev_pkg.evidence_status if ev_pkg else "NO_PACKAGE"
                
                # Check provider metadata
                provider = "NONE"
                provider_status = "NONE"
                if pipeline_res.evidence_items:
                    prov = pipeline_res.evidence_items[0].provenance or {}
                    provider = prov.get("provider", "NONE")
                    provider_status = prov.get("provider_status", "NONE")
                elif ev_pkg and ev_pkg.evidence_items:
                    prov = ev_pkg.evidence_items[0].provenance or {}
                    provider = prov.get("provider", "NONE")
                    provider_status = prov.get("provider_status", "NONE")

                record = {
                    "category": cat,
                    "query": q,
                    "model": pipeline_res.selected_model,
                    "mode": pipeline_res.decision.conversation_mode,
                    "task_type": pipeline_res.decision.task_type,
                    "complexity": pipeline_res.decision.complexity,
                    "action": action_name,
                    "requires_world_access": req_world,
                    "provider": provider,
                    "provider_status": provider_status,
                    "evidence_status": ev_status,
                    "evidence_count": len(pipeline_res.evidence_items) if pipeline_res.evidence_items else 0,
                    "raw_response": response_text,
                    "final_answer": eval_res.repaired_text,
                    "eval_score": eval_res.score,
                    "persona_issues": eval_res.persona_issues,
                    "latency_sec": round(elapsed, 2),
                    "prompt_snippet": pipeline_res.prompt[:300]
                }
                
                results.append(record)
                print(f"[{cat}] Query: '{q[:30]}...' -> Model: {record['model']}, Action: {record['action']}, World: {record['requires_world_access']}, Status: {record['provider_status']}, Eval: {record['eval_score']}", flush=True)
                
                with open("tests/reliability/diagnostic_raw_output.json", "w", encoding="utf-8") as f:
                    json.dump({"results": results}, f, indent=2)

            except Exception as e:
                print(f"[{cat}] Query: '{q}' -> ERROR: {str(e)}", flush=True)
                results.append({
                    "category": cat,
                    "query": q,
                    "error": str(e)
                })


    # Category M — Streaming vs Normal Comparison
    print("\n--- Running Category M (Streaming vs Normal Comparison) ---")
    m_results = []
    for q in STREAMING_COMPARISON_QUERIES:
        req = ChatRequest(message=q, conversation_id="sprint0-stream-session")
        try:
            # Normal
            res_normal = _execute_chat_pipeline(req)
            resp_normal = call_model(res_normal.prompt, model=res_normal.selected_model)
            
            # Streaming
            res_stream = _execute_chat_pipeline(req)
            chunks = list(stream_model(res_stream.prompt, model=res_stream.selected_model))
            resp_stream = "".join(chunks)
            
            m_results.append({
                "query": q,
                "model_normal": res_normal.selected_model,
                "model_stream": res_stream.selected_model,
                "resp_normal": resp_normal[:150],
                "resp_stream": resp_stream[:150],
                "parity": (res_normal.selected_model == res_stream.selected_model)
            })
            print(f"[M] Query: '{q[:30]}...' -> Parity: {res_normal.selected_model == res_stream.selected_model}")
        except Exception as e:
            print(f"[M] Query: '{q}' -> ERROR: {str(e)}")

    output_data = {
        "results": results,
        "streaming_comparison": m_results
    }

    with open("tests/reliability/diagnostic_raw_output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print("\nDiagnostic run complete. Results saved to tests/reliability/diagnostic_raw_output.json")


if __name__ == "__main__":
    run_diagnostics()
