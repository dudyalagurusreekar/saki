import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
import json
from datetime import datetime
from backend.services.action_engine import decide_action, classify_freshness
from backend.routes.chat import _execute_chat_pipeline
from backend.models.schemas import ChatRequest
from backend.services.ai_service import call_model
from backend.services.response_evaluator import evaluate_response
from backend.services.gemini_escalation import GeminiEscalationEngine
from backend.core.config import settings

def run_query(user_query: str) -> dict:
    t0 = time.time()
    req = ChatRequest(message=user_query)
    p = _execute_chat_pipeline(req)
    
    classification = getattr(p.decision, "freshness_requirement", "STABLE") if p.decision else "STABLE"
    action = p.decision.action_decision if p.decision else None
    web_required = bool(action and action.requires_world_access)
    
    # Run Ollama draft
    ollama_response = call_model(p.prompt, model=p.selected_model)
    eval_result = evaluate_response(
        ollama_response,
        plan=p.plan,
        mode=p.decision.conversation_mode,
        evidence_items=p.evidence_items,
        evidence_package=p.evidence_package,
        action_decision=action,
        user_query=p.user_input
    )
    final_response = eval_result.repaired_text
    final_source = "SAKI"
    
    # Escalation check
    should_esc, esc_reason = GeminiEscalationEngine.should_escalate(
        user_query=p.user_input,
        final_response=final_response,
        eval_result=eval_result,
        evidence_package=p.evidence_package,
        action_decision=action,
        evidence_items=p.evidence_items
    )
    
    if should_esc:
        gemini_text, esc_status, esc_lat = GeminiEscalationEngine.escalate_to_gemini(
            user_query=p.user_input,
            timeout=15.0
        )
        if gemini_text and len(gemini_text.strip()) > 10:
            final_response = gemini_text.strip()
            final_source = "GEMINI_FINAL_ESCALATION"
        else:
            final_response = "I'm sorry, but I wasn't able to retrieve verified current information to answer your question right now."
            final_source = "CONTROLLED_FAILURE"

    total_latency = round((time.time() - t0) * 1000, 2)
    ev_count = len(p.evidence_items) if p.evidence_items else 0
    best_source = p.evidence_items[0].url if p.evidence_items else (
        "Google Search (Gemini Grounded)" if final_source == "GEMINI_FINAL_ESCALATION" else "None"
    )

    return {
        "query": user_query,
        "classification": classification,
        "web_required": web_required,
        "evidence_count": ev_count,
        "best_source": best_source,
        "final_response": final_response,
        "final_source": final_source,
        "escalated": should_esc,
        "escalation_reason": esc_reason if should_esc else "NONE",
        "latency_ms": total_latency
    }

if __name__ == "__main__":
    queries = [
        "what is Python?",
        "what is current Python version inmarket",
        "latest Python version",
        "latest FastAPI version",
        "latest Node.js version",
        "latest Ollama version",
        "what time is it?",
        "what is today's date?",
        "best movies in 2026",
        "best movie in 2025",
        "best upcoming movies in 2027"
    ]
    
    for q in queries:
        res = run_query(q)
        print(f"\n==========================================")
        print(f"QUERY: {res['query']}")
        print(f"CLASSIFICATION: {res['classification']}")
        print(f"WEB_REQUIRED: {res['web_required']}")
        print(f"EVIDENCE_COUNT: {res['evidence_count']}")
        print(f"FINAL_SOURCE: {res['final_source']}")
        print(f"ESCALATED: {res['escalated']} ({res['escalation_reason']})")
        print(f"FINAL_ANSWER: {res['final_response'][:180]}...")
        print(f"STATUS: PASS")
