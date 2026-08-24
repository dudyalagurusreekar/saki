"""
Master Behavioral Benchmark Evaluation Suite for Saki Conversational Voice Brain
Evaluates all 23 pillars of the Saki Master Human-Like Conversational Voice Behavior Specification:
- Understanding before responding (Expression vs Need)
- Contextual emotional routing without naive keyword dependency
- Response length adaptivity (Ultra-Concise vs Balanced vs Deep Structured)
- Validate-Before-Solve emotional strategy (no unsolicited 5+ bullet advice dumps)
- Multilingual naturalness & code-mixing (English, Telugu, Kannada)
- Invisible model orchestration across Phi-3, Hermes 2, Qwen 3, Qwen Coder, Gemma
- Selective durable memory admission & cross-lingual retrieval
- Response quality evaluation (PASS, MINOR_ISSUE, REGENERATE)
- Voice pipeline integrity, 2-second silence window, and interruption latency instrumentation
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.saki_state import SakiCognitiveState
from backend.services.emotional_support_service import (
    emotional_support_service,
    SupportAssessment,
    SupportType
)
from backend.services.response_planner import (
    plan_response,
    ResponsePlan,
    ResponseType,
    AdaptiveLength
)
from backend.services.response_evaluator import (
    evaluate_response,
    QualityStatus,
    EvaluationResult
)
from backend.services.orchestrator import SakiModelOrchestrator
from backend.services.multilingual_service import multilingual_service, LanguageProfile
from backend.services.memory_admission import (
    MemoryAdmissionEngine,
    MemoryCandidate,
    SOURCE_USER,
    TYPE_PERSONAL_MEMORY
)
from backend.core.saki_persona import build_saki_system_prompt, format_prompt_for_model
from backend.core.config import settings


class TestMasterVoiceBehavior:
    """Master Behavioral Suite testing all core pillars of the Saki Unified Conversational Voice Brain."""

    # -------------------------------------------------------------
    # 1. CONVERSATION BREVITY & ADAPTIVE DEPTH
    # -------------------------------------------------------------
    def test_01_greetings_are_ultra_concise(self):
        """Greetings should trigger ULTRA_CONCISE adaptive length (1-2 sentences)."""
        state = SakiCognitiveState()
        state.conversation.mode = "casual"

        greetings = ["Morning", "Good morning", "Hey Saki", "Hi Saki", "Hello", "Yo"]
        for g in greetings:
            plan = plan_response(state, g)
            assert plan.adaptive_length == AdaptiveLength.ULTRA_CONCISE, f"Greeting '{g}' should be ULTRA_CONCISE, got {plan.adaptive_length}"
            assert plan.depth == "concise"

    def test_02_acknowledgements_are_ultra_concise(self):
        """Single acknowledgements ('Did you understand?', 'Got it?') must be ULTRA_CONCISE."""
        state = SakiCognitiveState()
        state.conversation.mode = "casual"

        acks = ["Did you understand?", "Did you get it?", "Got it?", "You there?", "Thanks Saki"]
        for a in acks:
            plan = plan_response(state, a)
            assert plan.adaptive_length == AdaptiveLength.ULTRA_CONCISE, f"Ack '{a}' should be ULTRA_CONCISE, got {plan.adaptive_length}"

    def test_03_deep_technical_queries_are_deep_structured(self):
        """Complex engineering / architecture queries must trigger DEEP_STRUCTURED length."""
        state = SakiCognitiveState()
        state.conversation.mode = "builder"
        state.conversation.task = "architecture_design"

        query = "Explain the architecture of our distributed microservices and why this approach is better than a monolith."
        plan = plan_response(state, query)
        assert plan.adaptive_length == AdaptiveLength.DEEP_STRUCTURED
        assert plan.technical_detail == "high"

    # -------------------------------------------------------------
    # 2. SEPARATING USER EXPRESSION VS USER NEED (3 DISAPPOINTMENT SCENARIOS)
    # -------------------------------------------------------------
    def test_04_pure_disappointment_expression_triggers_pure_emotional_validation(self):
        """
        User: 'I failed my interview.'
        Expression: Failure / Disappointment
        Need: Emotional acknowledgement & validation (no unsolicited advice checklist).
        """
        query = "I failed my interview."
        assessment = emotional_support_service.assess_support_need(query)
        assert assessment.support_type in [SupportType.EMOTIONAL_SUPPORT_NEED, SupportType.EMOTIONAL_EXPRESSION, SupportType.HIGH_PRIORITY_DISTRESS]
        assert assessment.solution_readiness < 0.35

        state = SakiCognitiveState()
        state.conversation.mode = "support"
        state.conversation.task = "emotional_support"
        state.user_state.emotion = "sad"
        state.user_state.intensity = assessment.emotion_intensity

        plan = plan_response(state, query, support_assessment=assessment)
        assert plan.response_type == ResponseType.PURE_EMOTIONAL
        assert plan.validate_before_solve is True
        assert "DO NOT jump into unsolicited advice" in plan.directive_prompt

    def test_05_disappointment_with_explicit_request_triggers_practical_guidance(self):
        """
        User: 'I failed my interview. Tell me exactly what I should improve.'
        Expression: Disappointment
        Need: Practical guidance + brief acknowledgement.
        """
        query = "I failed my interview. Tell me exactly what I should improve."
        assessment = emotional_support_service.assess_support_need(query)
        assert assessment.solution_readiness >= 0.50

        state = SakiCognitiveState()
        state.conversation.mode = "support"
        state.conversation.task = "mixed_support_practical"
        state.user_state.emotion = "sad"

        plan = plan_response(state, query, support_assessment=assessment)
        assert plan.response_type == ResponseType.MIXED_EMOTIONAL_PRACTICAL
        assert "Acknowledge the user's feelings" in plan.directive_prompt or "practical direction" in plan.directive_prompt or "next step" in plan.directive_prompt

    def test_06_mixed_distress_triggers_validate_first_then_support(self):
        """
        User: 'I failed my interview and honestly feel terrible about it.'
        Need: Deep emotional support & presence first.
        """
        query = "I failed my interview and honestly feel terrible about it."
        assessment = emotional_support_service.assess_support_need(query)
        assert assessment.emotion_intensity >= 0.60
        assert assessment.support_need >= 0.60

        state = SakiCognitiveState()
        state.conversation.mode = "support"
        state.conversation.task = "emotional_support"

        plan = plan_response(state, query, support_assessment=assessment)
        assert plan.validate_before_solve is True
        assert plan.tone == "empathetic_gentle"

    # -------------------------------------------------------------
    # 3. EMOTIONAL SUPPORT ROUTING (HERMES AS CAPABILITY, NOT IDENTITY)
    # -------------------------------------------------------------
    def test_07_hermes_activates_for_genuine_emotional_need(self):
        """Deep loneliness / severe distress activates Hermes without requiring naive keywords."""
        decision = SakiModelOrchestrator.route_request("I haven't talked to anyone in three days and I feel so isolated")
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_08_coder_activates_for_technical_bug_with_mild_frustration(self):
        """Frustrated with syntax error -> Coder (NOT Hermes). Technical intent dominates."""
        decision = SakiModelOrchestrator.route_request("I am so tired of this TypeError: NoneType object is not subscriptable in line 42")
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_09_casual_greeting_activates_phi3(self):
        """Simple greeting -> fast Phi-3."""
        decision = SakiModelOrchestrator.route_request("Good morning Saki, how are you?")
        assert decision.selected_model == settings.MODEL_PHI3
        assert decision.conversation_mode == "casual"

    def test_10_reasoning_activates_qwen3(self):
        """Complex algorithmic problem -> Qwen 3 reasoning."""
        decision = SakiModelOrchestrator.route_request("Analyze the time complexity trade-offs between merge sort and quicksort under worst-case scenarios")
        assert decision.selected_model == settings.MODEL_QWEN
        assert decision.conversation_mode == "thinking"

    # -------------------------------------------------------------
    # 4. SAKI UNIFIED PERSONA & CHATML ADAPTATION
    # -------------------------------------------------------------
    def test_11_chatml_formatting_for_hermes_preserves_unified_identity(self):
        """Nous Hermes prompt must use ChatML (<|im_start|>) and contain Saki's unified identity."""
        sys_prompt = build_saki_system_prompt(mode="support", language="en")
        user_msg = "I feel so overwhelmed by everything."
        formatted = format_prompt_for_model(settings.MODEL_HERMES, sys_prompt, user_msg)

        assert "<|im_start|>system" in formatted
        assert "You are Saki." in formatted
        assert "<|im_start|>user" in formatted
        assert "<|im_start|>assistant" in formatted

    # -------------------------------------------------------------
    # 5. MULTILINGUAL CODE-MIXING & IDENTITY INTEGRITY
    # -------------------------------------------------------------
    def test_12_telugu_code_mixing_detection(self):
        """Code-mixed Telugu ('Ee project lo FastAPI error enduku vastundi?') is classified as te."""
        query = "Ee project lo FastAPI error enduku vastundi?"
        profile = multilingual_service.classify_text(query)
        assert profile.language == "te", f"Expected 'te', got {profile.language}"
        assert profile.is_mixed is True

    def test_12b_romanized_telugu_greeting_detection(self):
        """Romanized Telugu greeting ('namaskaram saki ela unnavu') is classified as te."""
        query = "namaskaram saki ela unnavu"
        profile = multilingual_service.classify_text(query)
        assert profile.language == "te", f"Expected 'te', got {profile.language}"

    def test_12c_telugu_system_prompt_directive(self):
        """Telugu system prompt directive contains explicit instruction to reply in authentic Telugu."""
        prompt = build_saki_system_prompt(language="te")
        assert "MULTILINGUAL DIRECTIVE (Telugu / తెలుగు)" in prompt
        assert "You MUST generate your response in authentic, natural, conversational Telugu" in prompt

    def test_13_kannada_query_detection(self):
        """Kannada script query is classified as Kannada."""
        query = "ಈ ಪ್ರಾಜೆಕ್ಟ್‌ನಲ್ಲಿ ಬಗ್ ಹೇಗೆ ಸರಿಪಡಿಸುವುದು?"
        profile = multilingual_service.classify_text(query)
        assert profile.language == "kn"
        assert profile.indic_script == "kannada"

    def test_14_cross_lingual_memory_keyword_expansion(self):
        """Query in Telugu expands cross-lingually to retrieve English concepts."""
        expanded = multilingual_service.expand_memory_query_terms("నాకు పైథాన్ అంటే ఇష్టం")
        assert "python" in expanded
        assert "preference" in expanded or "favorite" in expanded

    # -------------------------------------------------------------
    # 6. SELECTIVE MEMORY ADMISSION
    # -------------------------------------------------------------
    def test_15_selective_memory_admits_durable_facts_and_rejects_casual(self):
        """Durable facts/preferences are admitted; transient remarks are rejected."""
        # 1. Durable user preference -> Admitted
        cand_durable = MemoryCandidate(
            content="I prefer dark mode in all my IDEs and always write in TypeScript.",
            memory_type=TYPE_PERSONAL_MEMORY,
            source_type=SOURCE_USER
        )
        decision_durable = MemoryAdmissionEngine.evaluate_candidate(cand_durable)
        assert decision_durable.admit is True

        # 2. Transient casual greeting -> Rejected
        cand_transient = MemoryCandidate(
            content="Good morning, I just woke up.",
            memory_type="CASUAL_CONVERSATION",
            source_type=SOURCE_USER
        )
        decision_transient = MemoryAdmissionEngine.evaluate_candidate(cand_transient)
        assert decision_transient.admit is False

    # -------------------------------------------------------------
    # 7. RESPONSE QUALITY EVALUATOR (PASS, MINOR_ISSUE, REGENERATE)
    # -------------------------------------------------------------
    def test_16_response_evaluator_passes_clean_response(self):
        """Clean, natural conversational response passes with PASS status."""
        draft = "Good morning! 😊 Ready to build something great today?"
        res = evaluate_response(draft, mode="casual")
        assert res.passed is True
        assert res.status == QualityStatus.PASS
        assert res.needs_regeneration is False

    def test_17_response_evaluator_sanitizes_robotic_cliches(self):
        """Robotic cliches are scrubbed with MINOR_ISSUE status."""
        draft = "How may I assist you today? I am an AI model. Here is what we can do."
        res = evaluate_response(draft, mode="casual")
        assert "How may I assist you" not in res.repaired_text
        assert "I am an AI" not in res.repaired_text
        assert res.status == QualityStatus.MINOR_ISSUE

    def test_18_response_evaluator_flags_empty_or_degraded_response_for_regen(self):
        """Empty response is flagged with REGENERATE status."""
        draft = ""
        res = evaluate_response(draft, mode="casual")
        assert res.status == QualityStatus.REGENERATE
        assert res.needs_regeneration is True

    # -------------------------------------------------------------
    # 8. VOICE PIPELINE & 2-SECOND SILENCE WINDOW
    # -------------------------------------------------------------
    def test_19_continuous_voice_2sec_window_constant(self):
        """Frontend AudioRecorder silence timeout must default to 2000ms."""
        # Verify 2000ms silence timeout in AudioRecorder.ts
        recorder_path = os.path.join(os.path.dirname(__file__), "../../frontend/src/components/core/engine/AudioRecorder.ts")
        with open(recorder_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "DEFAULT_SILENCE_TIMEOUT_MS = 2000;" in content, "DEFAULT_SILENCE_TIMEOUT_MS must be 2000ms"

    def test_20_interruption_controller_instruments_real_latency(self):
        """Interruption controller triggers interruption and instruments actual latency in ms."""
        from backend.services.interruption_controller import interruption_controller
        record = interruption_controller.trigger_interruption("test-session", reason="user_barge_in")
        assert record.interruption_id is not None
        assert record.reaction_latency_ms >= 0.0
        assert isinstance(record.reaction_latency_ms, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
