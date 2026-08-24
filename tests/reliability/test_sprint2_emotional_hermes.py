"""
Sprint 2 — Advanced Emotional Intelligence & Hermes 2 Routing Test Suite

Validates:
1. Explicit emotional support requests activate Hermes 2 with validate-before-solve.
2. Implicit sadness/disappointment (without explicit emotion words) activates Hermes 2.
3. Personal disclosure and self-doubt/imposter syndrome activate Hermes 2.
4. Repeated frustration trajectory triggers context-dependent withdrawal/resignation detection.
5. Mild frustration during coding tasks stays on Qwen 2.5 Coder with calm empathetic tone.
6. Mixed emotional + practical requests preserve both intents (validates, then guides).
7. Three-way disambiguation of failure scenarios (Pure Emotion vs Mixed vs Deep Venting).
8. Practical requests with emotional wording do not cause false-positive Hermes routing.
9. Anti-flapping model stability margins prevent erratic model jumping.
10. Emotional trajectory tracking recovers back to casual/thinking models when normalized.
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.services.emotional_support_service import (
    SupportAssessmentEngine,
    SupportAssessment,
    SupportType,
    HermesActivationLevel,
    TemporalEmotionTracker
)
from backend.services.orchestrator import SakiModelOrchestrator, RoutingDecision
from backend.services.response_planner import plan_response, ResponseType
from backend.services.brain_engine import brain_engine
from backend.models.schemas import ChatRequest

client = TestClient(app)


class TestSprint2EmotionalHermes:

    def test_01_explicit_emotional_support_routes_to_hermes(self):
        """(1) Proves explicit emotional support requests activate Hermes 2 with pure emotional validation."""
        query = "I feel so lonely, overwhelmed, and completely exhausted today."
        assessment = SupportAssessmentEngine.evaluate(query)

        assert assessment.support_type in [SupportType.EMOTIONAL_SUPPORT_NEED, SupportType.HIGH_PRIORITY_DISTRESS]
        assert assessment.activation_level == HermesActivationLevel.HIGH
        assert assessment.solution_readiness <= 0.30
        assert assessment.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD

        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.support_assessment.activation_level == HermesActivationLevel.HIGH

        plan = plan_response(decision.cognitive_state, query, support_assessment=decision.support_assessment)
        assert plan.response_type == ResponseType.PURE_EMOTIONAL
        assert plan.validate_before_solve is True
        assert "DO NOT jump into unsolicited advice" in plan.directive_prompt

    def test_02_implicit_sadness_disappointment_without_emotion_words(self):
        """(2) Proves implicit loss/disappointment without explicit emotion words activates Hermes 2."""
        query = "Poured weeks of intense work into this proposal and they just shut down the project without explanation."
        assessment = SupportAssessmentEngine.evaluate(query)

        assert assessment.support_type in [SupportType.EMOTIONAL_SUPPORT_NEED, SupportType.MIXED_SUPPORT_PRACTICAL]
        assert assessment.activation_level == HermesActivationLevel.HIGH
        assert assessment.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD
        assert "shut down" in assessment.cause or "disappointment" in assessment.cause or "project" in assessment.cause

        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_03_personal_disclosure_and_imposter_syndrome(self):
        """(3) Proves vulnerability and self-doubt/imposter syndrome activate Hermes 2."""
        query = "Everyone else on my team seems so much smarter. I feel like an imposter and that I don't belong here."
        assessment = SupportAssessmentEngine.evaluate(query)

        assert assessment.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert assessment.activation_level == HermesActivationLevel.HIGH
        assert assessment.support_need >= 0.70

        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_04_repeated_frustration_context_dependent_resignation(self):
        """(4) Proves short ambiguous phrases ('Whatever, it's fine') in context of repeated failure route to Hermes."""
        # 1. Neutral baseline without prior distress
        assessment_neutral = SupportAssessmentEngine.evaluate("Whatever, it's fine.", recent_history=[])
        assert assessment_neutral.support_type == SupportType.NORMAL_CONVERSATION
        assert assessment_neutral.activation_level == HermesActivationLevel.NONE

        # 2. Context with multiple prior failed attempts & errors
        frustrated_history = [
            {"user": "FastAPI websocket endpoint is throwing 500 error again."},
            {"user": "Still broken after updating CORS, this is so frustrating."},
            {"user": "Now the connection is dropping entirely."}
        ]
        assessment_distressed = SupportAssessmentEngine.evaluate(
            "Whatever, it's fine.",
            recent_history=frustrated_history
        )

        assert assessment_distressed.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert assessment_distressed.activation_level == HermesActivationLevel.HIGH
        assert assessment_distressed.support_need >= 0.70

        decision = SakiModelOrchestrator.classify_request("Whatever, it's fine.", recent_history=frustrated_history)
        assert decision.selected_model == settings.MODEL_HERMES

    def test_05_mild_frustration_in_coding_stays_on_coder(self):
        """(5) Proves mild frustration during coding tasks keeps Qwen 2.5 Coder while adding calm tone."""
        query = "Ugh, this TypeScript compiler error with generic constraints is so annoying and frustrating, fix it for me."
        assessment = SupportAssessmentEngine.evaluate(query)

        assert assessment.support_type == SupportType.PRACTICAL_WITH_EMOTION
        assert assessment.activation_level == HermesActivationLevel.LOW
        assert assessment.solution_readiness >= 0.85

        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

        plan = plan_response(decision.cognitive_state, query, support_assessment=decision.support_assessment)
        assert plan.response_type == ResponseType.PRACTICAL_WITH_EMOTION
        assert plan.acknowledge_emotion is True
        assert plan.technical_detail == "high"

    def test_06_mixed_support_practical_preserves_both_intents(self):
        """(6) Proves mixed emotional + practical requests preserve both intents with validate-then-solve."""
        query = "I failed my system design interview yesterday, tell me what I should improve."
        assessment = SupportAssessmentEngine.evaluate(query)

        assert assessment.support_type == SupportType.MIXED_SUPPORT_PRACTICAL
        assert assessment.primary_intent == "emotional_support"
        assert assessment.secondary_intent == "practical_direction"
        assert assessment.solution_readiness >= 0.50

        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

        plan = plan_response(decision.cognitive_state, query, support_assessment=decision.support_assessment)
        assert plan.response_type == ResponseType.MIXED_EMOTIONAL_PRACTICAL
        assert plan.validate_before_solve is True
        assert "first in 1-2 warm, grounded sentences" in plan.directive_prompt or "First, recognize" in plan.directive_prompt

    def test_07_three_way_interview_failure_disambiguation(self):
        """(7) Disambiguates three distinct forms of interview failure expressions."""
        # A: Pure statement of failure -> High support, low solution readiness
        res_a = SupportAssessmentEngine.evaluate("I failed my interview.")
        assert res_a.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert res_a.activation_level == HermesActivationLevel.HIGH
        assert res_a.solution_readiness <= 0.35

        # B: Failure with explicit practical improvement request -> Mixed support + practical
        res_b = SupportAssessmentEngine.evaluate("I failed my interview, tell me what I should improve.")
        assert res_b.support_type == SupportType.MIXED_SUPPORT_PRACTICAL
        assert res_b.activation_level == HermesActivationLevel.HIGH
        assert res_b.solution_readiness >= 0.50

        # C: Failure with explicit emotional venting -> Deep support need
        res_c = SupportAssessmentEngine.evaluate("I failed my interview and honestly feel terrible about it.")
        assert res_c.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert res_c.activation_level == HermesActivationLevel.HIGH
        assert res_c.solution_readiness <= 0.25

    def test_08_practical_request_with_positive_emotion_no_false_positive(self):
        """(8) Proves positive emotion with coding task does not falsely trigger Hermes."""
        query = "I love building React applications with Tailwind! Write a custom useDebounce hook in TypeScript."
        assessment = SupportAssessmentEngine.evaluate(query)

        assert assessment.support_type in [SupportType.NORMAL_CONVERSATION, SupportType.EMOTIONAL_EXPRESSION, SupportType.PRACTICAL_WITH_EMOTION]
        assert assessment.activation_level != HermesActivationLevel.HIGH

        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_09_anti_flapping_stability_logic(self):
        """(9) Proves anti-flapping stability prevents bouncing during active technical sessions."""
        # In an active Builder session (previous_model = MODEL_CODER)
        query = "Show me the next step for adding authentication middleware."
        
        decision = SakiModelOrchestrator.classify_request(
            query=query,
            previous_model=settings.MODEL_CODER
        )
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.should_switch_model is False

        # Strong emotional shift overrides stability immediately
        distress_query = "I feel completely overwhelmed and can't do this anymore."
        decision_override = SakiModelOrchestrator.classify_request(
            query=distress_query,
            previous_model=settings.MODEL_CODER
        )
        assert decision_override.selected_model == settings.MODEL_HERMES
        assert decision_override.should_switch_model is True

    def test_10_temporal_trajectory_tracking_and_normalization_recovery(self):
        """(10) Proves temporal trajectory tracks escalation and smoothly normalizes back to casual model."""
        tracker = TemporalEmotionTracker(max_turns=10)

        # 1. Escalating turns
        t1_assessment = SupportAssessmentEngine.evaluate("Everything is failing today.")
        tracker.record_turn("Everything is failing today.", t1_assessment)

        t2_assessment = SupportAssessmentEngine.evaluate("I'm so exhausted and hopeless.")
        tracker.record_turn("I'm so exhausted and hopeless.", t2_assessment)

        traj_escalated = tracker.get_recent_trajectory()
        assert traj_escalated["trend"] == "escalating"
        assert traj_escalated["negative_turn_count"] >= 2

        # 2. Recovery / Normalization turns
        t3_assessment = SupportAssessmentEngine.evaluate("Thanks Saki, that perspective helped a lot.")
        tracker.record_turn("Thanks Saki, that perspective helped a lot.", t3_assessment)

        t4_assessment = SupportAssessmentEngine.evaluate("What is the current time in Tokyo?")
        tracker.record_turn("What is the current time in Tokyo?", t4_assessment)

        traj_recovered = tracker.get_recent_trajectory()
        assert traj_recovered["trend"] in ["deescalating", "stable"]

        # Subsequent query routes back to casual model
        decision_norm = SakiModelOrchestrator.classify_request("Good morning Saki, hope you have a great day!")
        assert decision_norm.selected_model == settings.MODEL_PHI3
