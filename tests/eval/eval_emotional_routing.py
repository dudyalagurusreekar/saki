import os
import sys
import time
from typing import List, Dict, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.services.orchestrator import SakiModelOrchestrator
from backend.services.emotional_support_service import SupportAssessmentEngine, SupportType, HermesActivationLevel
from backend.core.config import settings

BENCHMARK_CASES = [
    # -------------------------------------------------------------
    # CATEGORY A: SHOULD ACTIVATE HERMES (Pure / High Emotional Support)
    # -------------------------------------------------------------
    {
        "id": "A1",
        "category": "CATEGORY_A",
        "description": "Persistent loneliness & social disconnection",
        "query": "I've been feeling so lonely lately and feel like nobody really cares about me.",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.70
    },
    {
        "id": "A2",
        "category": "CATEGORY_A",
        "description": "Discouragement after multi-week project failure",
        "query": "I worked on this project for three solid weeks and it completely failed. I feel like a total failure.",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.70
    },
    {
        "id": "A3",
        "category": "CATEGORY_A",
        "description": "Explicit request for emotional presence / listening",
        "query": "I really need someone to listen to me right now. Everything feels completely overwhelming.",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.75
    },
    {
        "id": "A4",
        "category": "CATEGORY_A",
        "description": "Personal betrayal and grief",
        "query": "My close friend betrayed my trust and I feel heartbroken and completely lost.",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.70
    },
    {
        "id": "A5",
        "category": "CATEGORY_A",
        "description": "Severe anxiety / panic distress",
        "query": "I'm having a severe panic attack right now, my chest feels tight and I'm terrified.",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.85
    },
    {
        "id": "A6",
        "category": "CATEGORY_A",
        "description": "Vulnerability and imposter syndrome",
        "query": "I feel so useless at my job and keep thinking I don't belong here at all.",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.70
    },

    # -------------------------------------------------------------
    # CATEGORY B: SHOULD NOT AUTOMATICALLY ACTIVATE HERMES (Technical / Practical / Casual)
    # -------------------------------------------------------------
    {
        "id": "B1",
        "category": "CATEGORY_B",
        "description": "Frustrated with Python bug + direct fix command",
        "query": "I'm frustrated with this Python TypeError exception. Fix it for me.",
        "history": [],
        "expected_model": settings.MODEL_CODER,
        "expected_mode": "builder",
        "should_activate_hermes": False,
        "max_support_need": 0.40
    },
    {
        "id": "B2",
        "category": "CATEGORY_B",
        "description": "Tired user asking for syntax",
        "query": "I'm so tired tonight. What's the syntax for a dictionary comprehension in Python?",
        "history": [],
        "expected_model": settings.MODEL_CODER,
        "expected_mode": "builder",
        "should_activate_hermes": False,
        "max_support_need": 0.35
    },
    {
        "id": "B3",
        "category": "CATEGORY_B",
        "description": "Annoying API endpoint bug",
        "query": "This FastAPI endpoint is annoying. How do I fix the CORS headers?",
        "history": [],
        "expected_model": settings.MODEL_CODER,
        "expected_mode": "builder",
        "should_activate_hermes": False,
        "max_support_need": 0.35
    },
    {
        "id": "B4",
        "category": "CATEGORY_B",
        "description": "Excitement about deep algorithm learning",
        "query": "I'm so excited about neural networks! Can you explain backpropagation mathematically?",
        "history": [],
        "expected_model": settings.MODEL_QWEN3,
        "expected_mode": "thinking",
        "should_activate_hermes": False,
        "max_support_need": 0.30
    },
    {
        "id": "B5",
        "category": "CATEGORY_B",
        "description": "Simple everyday greeting",
        "query": "Hey Saki, good morning! Are you ready for today?",
        "history": [],
        "expected_model": settings.MODEL_PHI3,
        "expected_mode": "casual",
        "should_activate_hermes": False,
        "max_support_need": 0.20
    },

    # -------------------------------------------------------------
    # CATEGORY C: MIXED SUPPORT + PRACTICAL
    # -------------------------------------------------------------
    {
        "id": "C1",
        "category": "CATEGORY_C",
        "description": "Disappointment about project failure + asking what next",
        "query": "I feel terrible about this project failing after all my hard work. What should I do next?",
        "history": [],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.60
    },

    # -------------------------------------------------------------
    # CATEGORY D: CONTEXT-DEPENDENT SHORT PHRASES
    # -------------------------------------------------------------
    {
        "id": "D1",
        "category": "CATEGORY_D",
        "description": "'Whatever, it's fine' after repeated failures -> Resignation / Distress",
        "query": "Whatever, it's fine.",
        "history": [
            {"user": "My build failed again with 15 errors.", "saki": "Let's inspect the error logs."},
            {"user": "Still broken. I've spent 4 hours on this and nothing works.", "saki": "Take a breath, let's look at it."}
        ],
        "expected_model": settings.MODEL_HERMES,
        "expected_mode": "support",
        "should_activate_hermes": True,
        "min_support_need": 0.70
    },
    {
        "id": "D2",
        "category": "CATEGORY_D",
        "description": "'Whatever, it's fine' in casual banter -> Casual acknowledgement",
        "query": "Whatever, it's fine.",
        "history": [
            {"user": "Did you want me to commit this?", "saki": "Sure, whenever you're ready."},
            {"user": "I will do it later tonight.", "saki": "Sounds like a solid plan."}
        ],
        "expected_model": settings.MODEL_PHI3,
        "expected_mode": "casual",
        "should_activate_hermes": False,
        "max_support_need": 0.20
    }
]


def run_evaluation_suite() -> Dict[str, Any]:
    print("=" * 70)
    print("SAKI ADVANCED EMOTIONAL ROUTING & HERMES ACTIVATION EVALUATION")
    print("=" * 70)

    total_cases = len(BENCHMARK_CASES)
    passed_cases = 0
    hermes_expected_count = sum(1 for c in BENCHMARK_CASES if c["should_activate_hermes"])
    non_hermes_expected_count = total_cases - hermes_expected_count

    true_positives = 0  # Hermes expected & activated
    false_positives = 0 # Hermes not expected, but activated
    true_negatives = 0  # Hermes not expected & not activated
    false_negatives = 0 # Hermes expected, but missed

    latencies = []

    for case in BENCHMARK_CASES:
        cid = case["id"]
        cat = case["category"]
        desc = case["description"]
        query = case["query"]
        history = case["history"]
        expected_hermes = case["should_activate_hermes"]
        expected_model = case["expected_model"]
        expected_mode = case["expected_mode"]

        t0 = time.perf_counter()
        decision = SakiModelOrchestrator.classify_request(
            query=query,
            recent_history=history
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)

        actual_hermes = (decision.selected_model == settings.MODEL_HERMES)
        assessment = decision.support_assessment

        # Scoring checks
        min_need = case.get("min_support_need", 0.0)
        max_need = case.get("max_support_need", 1.0)
        score_calibrated = (min_need <= decision.support_score <= max_need)

        # Hermes activation accuracy
        hermes_match = (actual_hermes == expected_hermes)
        model_match = (decision.selected_model == expected_model)
        mode_match = (decision.conversation_mode == expected_mode)

        if expected_hermes and actual_hermes:
            true_positives += 1
        elif not expected_hermes and actual_hermes:
            false_positives += 1
        elif not expected_hermes and not actual_hermes:
            true_negatives += 1
        elif expected_hermes and not actual_hermes:
            false_negatives += 1

        case_passed = hermes_match and model_match and mode_match and score_calibrated

        if case_passed:
            passed_cases += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"

        print(f"[{status}] {cid} ({cat}): {desc}")
        print(f"       Query: \"{query}\"")
        print(f"       Selected: {decision.selected_model} (mode: {decision.conversation_mode}) | Expected: {expected_model} ({expected_mode})")
        print(f"       Support Score: {decision.support_score:.2f} (level: {decision.support_level}) | Emotion: {decision.detected_emotion}")
        print(f"       Reason: {decision.reason}")
        print(f"       Latency: {latency_ms:.2f} ms\n")

    accuracy = (passed_cases / total_cases) * 100.0
    hermes_accuracy = ((true_positives + true_negatives) / total_cases) * 100.0
    avg_latency = sum(latencies) / len(latencies)

    print("=" * 70)
    print("EVALUATION SUMMARY RESULTS")
    print("=" * 70)
    print(f"Total Benchmark Test Cases:    {total_cases}")
    print(f"Passed All Criteria:           {passed_cases}/{total_cases} ({accuracy:.1f}%)")
    print(f"Hermes Activation Accuracy:    {hermes_accuracy:.1f}%")
    print(f"True Positives (Hermes):       {true_positives}/{hermes_expected_count}")
    print(f"True Negatives (Non-Hermes):   {true_negatives}/{non_hermes_expected_count}")
    print(f"False Positives (Over-activ):  {false_positives}")
    print(f"False Negatives (Missed Emo):  {false_negatives}")
    print(f"Average Routing Latency:       {avg_latency:.2f} ms")
    print("=" * 70)

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "accuracy": accuracy,
        "hermes_accuracy": hermes_accuracy,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "false_negatives": false_negatives,
        "avg_latency_ms": avg_latency
    }


if __name__ == "__main__":
    run_evaluation_suite()
