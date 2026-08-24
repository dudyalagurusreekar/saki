"""
SAKI — Emotional Support Routing, Multi-Signal Assessment & Hermes Activation Tests

Verifies:
1. Category A (Should Activate Hermes): Loneliness, multi-week project failure, anxiety, betrayal, vulnerability.
2. Category B (Should NOT Automatically Activate Hermes): Frustrated with Python bug + fix it, tired syntax request, annoying API bug, excited learning, neutral greetings.
3. Category C (Mixed Support + Practical): Project failure + what next, frustrated with Saki + help figure out why.
4. Category D (Context-Dependent): "Whatever, it's fine" after escalating failures vs after casual talk.
5. Validate-Before-Solve Prompt Construction & Response Quality Validation (no advice dumping, no robotic cliches).
6. ChatML prompt formatting for nous-hermes2:latest.
7. Diagnostic routing metadata (support_level, support_score, emotion, reason).
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.orchestrator import SakiModelOrchestrator
from backend.services.emotional_support_service import (
    SupportAssessmentEngine, 
    SupportType, 
    HermesActivationLevel
)
from backend.services.response_planner import plan_response
from backend.services.response_evaluator import evaluate_response
from backend.core.saki_persona import format_prompt_for_model, build_saki_system_prompt
from backend.core.config import settings

client = TestClient(app)


class TestEmotionalSupportRouting:

    # -------------------------------------------------------------
    # CATEGORY A: SHOULD ACTIVATE HERMES
    # -------------------------------------------------------------
    def test_category_a_loneliness_activates_hermes(self):
        """Persistent loneliness disclosure routes to nous-hermes2:latest in Support Mode."""
        query = "I've been feeling so lonely lately and feel like nobody really cares about me."
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.task_type == "emotional_support"
        assert decision.support_score >= 0.70
        assert decision.support_level == "high"
        assert decision.emotional_importance == "high"

    def test_category_a_three_week_failure_activates_hermes(self):
        """Discouragement after 3 weeks of work failing activates Hermes with specific situation context."""
        query = "I worked on this project for three solid weeks and it completely failed. I feel like a total failure."
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.support_score >= 0.70
        assert decision.detected_emotion in ["discouraged_by_failure", "vulnerable_self_doubt"]

    def test_category_a_explicit_listening_request_activates_hermes(self):
        """Explicit request for someone to listen activates Hermes."""
        query = "I really need someone to listen to me right now. Everything feels completely overwhelming."
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.support_assessment.solution_readiness < 0.30

    def test_category_a_panic_attack_distress_activates_hermes(self):
        """Severe anxiety / panic distress triggers High Priority Distress in Support Mode."""
        query = "I'm having a severe panic attack right now, my chest feels tight and I'm terrified."
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.support_assessment.support_type == SupportType.HIGH_PRIORITY_DISTRESS
        assert decision.support_score >= 0.85

    # -------------------------------------------------------------
    # CATEGORY B: SHOULD NOT AUTOMATICALLY ACTIVATE HERMES
    # -------------------------------------------------------------
    def test_category_b_frustrated_with_python_error_routes_to_coder(self):
        """Frustrated user with Python bug who asks to fix it routes to Qwen Coder, not Hermes."""
        query = "I'm frustrated with this Python TypeError exception. Fix it for me."
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"
        assert decision.task_type == "coding_task"
        assert decision.coding_required is True
        assert decision.support_assessment.support_type == SupportType.PRACTICAL_WITH_EMOTION
        assert decision.support_score <= 0.40

    def test_category_b_tired_asking_for_syntax_routes_to_coder(self):
        """Tired user asking for syntax routes to coding model with warm tone, not Hermes."""
        query = "I'm so tired tonight. What's the syntax for a dictionary comprehension in Python?"
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"
        assert decision.support_score <= 0.35

    def test_category_b_annoying_api_bug_routes_to_coder(self):
        """Annoying API endpoint bug routes to Coder."""
        query = "This FastAPI endpoint is annoying. How do I fix the CORS headers?"
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_category_b_excited_algorithm_routes_to_qwen3(self):
        """Excited user asking for algorithm math routes to Qwen3 (Thinking Mode)."""
        query = "I'm so excited about neural networks! Can you explain backpropagation mathematically?"
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"

    def test_category_b_casual_greeting_routes_to_phi3(self):
        """Casual greeting routes to fast Phi-3 model."""
        query = "Hey Saki, good morning! Are you ready for today?"
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_PHI3
        assert decision.conversation_mode == "casual"

    # -------------------------------------------------------------
    # CATEGORY C: MIXED SUPPORT + PRACTICAL
    # -------------------------------------------------------------
    def test_category_c_mixed_project_failure_what_next_routes_to_hermes(self):
        """User disappointed about project failure asking what next routes to Hermes (Validate first then guide)."""
        query = "I feel terrible about this project failing after all my hard work. What should I do next?"
        decision = SakiModelOrchestrator.classify_request(query=query)

        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.support_assessment.support_type == SupportType.MIXED_SUPPORT_PRACTICAL

    # -------------------------------------------------------------
    # CATEGORY D: CONTEXT-DEPENDENT SHORT PHRASES
    # -------------------------------------------------------------
    def test_category_d_whatever_after_repeated_failure_activates_hermes(self):
        """'Whatever, it's fine' after repeated failures is recognized as resignation / distress."""
        history = [
            {"user": "My build failed again with 15 errors.", "saki": "Let's inspect the error logs."},
            {"user": "Still broken. I've spent 4 hours on this and nothing works.", "saki": "Take a breath, let's look at it."}
        ]
        decision = SakiModelOrchestrator.classify_request(
            query="Whatever, it's fine.",
            recent_history=history
        )

        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.detected_emotion == "discouraged"
        assert decision.support_score >= 0.70

    def test_category_d_whatever_in_casual_context_routes_to_phi3(self):
        """'Whatever, it's fine' in casual context remains a normal casual remark."""
        history = [
            {"user": "Did you want me to commit this?", "saki": "Sure, whenever you're ready."},
            {"user": "I will do it later tonight.", "saki": "Sounds like a solid plan."}
        ]
        decision = SakiModelOrchestrator.classify_request(
            query="Whatever, it's fine.",
            recent_history=history
        )

        assert decision.selected_model == settings.MODEL_PHI3
        assert decision.conversation_mode == "casual"
        assert decision.support_score <= 0.20

    # -------------------------------------------------------------
    # PROMPT SYNTHESIS & CHATML FORMATTING
    # -------------------------------------------------------------
    def test_hermes_chatml_prompt_formatting(self):
        """Verifies that prompts sent to nous-hermes2:latest use ChatML syntax."""
        sys_prompt = "You are Saki. Be empathetic and supportive."
        user_msg = "I feel overwhelmed."
        formatted = format_prompt_for_model(settings.MODEL_HERMES, sys_prompt, user_msg)

        assert "<|im_start|>system" in formatted
        assert "<|im_end|>" in formatted
        assert "<|im_start|>user" in formatted
        assert "<|im_start|>assistant" in formatted

    def test_validate_before_solve_response_planner(self):
        """Verifies that ResponsePlan enforces validate-before-solve when support need is high."""
        query = "I worked so hard and failed. I feel like giving up."
        decision = SakiModelOrchestrator.classify_request(query=query)
        plan = plan_response(decision.cognitive_state, query, support_assessment=decision.support_assessment)

        assert plan.validate_before_solve is True
        assert plan.acknowledge_emotion is True
        assert "Validate Before Solve" in plan.directive_prompt

    # -------------------------------------------------------------
    # RESPONSE QUALITY EVALUATION & ANTI-CLICHE SCRUBBING
    # -------------------------------------------------------------
    def test_response_evaluator_simplifies_excessive_advice_bullets(self):
        """Verifies that response_evaluator flattens excessive advice checklists in Support Mode."""
        draft = (
            "I hear you. Take a breath.\n\n"
            "1. Take a 10 minute walk outside.\n"
            "2. Drink a glass of water.\n"
            "3. Meditate for 15 minutes.\n"
            "4. Get a good night's sleep.\n"
            "5. Journal your feelings."
        )
        res = evaluate_response(draft, mode="support")

        assert "excessive_advice_bullets_in_support_mode" in res.persona_issues
        # Numbered bullets should be simplified into natural sentences
        assert not res.repaired_text.startswith("1.")

    def test_response_evaluator_removes_robotic_assistant_cliches(self):
        """Verifies that robotic assistant tropes are cleanly stripped."""
        draft = "I hear you. How may I assist you today? As an AI model, I'm here for you."
        res = evaluate_response(draft, mode="support")

        assert any("robotic_cliche" in issue for issue in res.persona_issues)
        assert "How may I assist you today" not in res.repaired_text
        assert "As an AI model" not in res.repaired_text

    # -------------------------------------------------------------
    # END-TO-END CHAT API INTEGRATION
    # -------------------------------------------------------------
    def test_chat_api_hermes_routing_diagnostics(self):
        """End-to-end test verifying /api/chat returns full support routing diagnostics."""
        with patch("backend.routes.chat.call_model", return_value="I hear you. It's completely understandable to feel drained after pouring so much energy into this."):
            res = client.post("/api/chat", json={
                "message": "I worked on this project for three solid weeks and it failed. I feel like giving up.",
                "conversation_id": "test-hermes-session"
            })

            assert res.status_code == 200
            data = res.json()
            assert data["mode"] == "support"
            assert data["routing"]["selected_model"] == settings.MODEL_HERMES
            assert data["routing"]["support_level"] in ["high", "moderate"]
            assert data["routing"]["support_score"] >= 0.70
            assert "understandable" in data["response"]
