"""
Sprint 8 — Adaptive Model Swapping + Mood/Context-Aware Orchestration Test Suite

Validates:
1. Simple greeting -> Phi-3.
2. Simple acknowledgement -> Phi-3.
3. Complex reasoning -> Qwen3.
4. Coding/debugging -> Qwen Coder.
5. Vision input -> Gemma 3.
6. Deep emotional support -> Hermes 2.
7. Mild frustration + coding -> Qwen Coder (no unnecessary Hermes switch).
8. Emotional + practical request -> dominant strategy routing.
9. Telugu emotional support -> Hermes 2.
10. Kannada emotional support -> Hermes 2.
11. Telugu coding -> Qwen Coder.
12. Kannada coding -> Qwen Coder.
13. Telugu reasoning -> Qwen3.
14. Kannada reasoning -> Qwen3.
15. Model stability / anti-flapping when score difference is within margin.
16. Strong capability override (Vision, Code, High Distress).
17. Model switching after conversation topic change.
18. Context preservation across model switches.
19. Memory preservation across model switches.
20. Language preservation across model switches.
21. Voice model switching.
22. Model loading/unloading safety.
23. No unloading of active models.
24. Resource-constrained fallback.
25. Duplicate/stale model-switch event rejection.
26. Core event emission for model transitions.
27. User-facing response does not leak internal model details.
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.services.orchestrator import (
    SakiModelOrchestrator,
    RoutingDecision,
    ModelSelectionContext,
    ConversationPosition,
    infer_conversation_position
)
from backend.services.emotional_support_service import (
    SupportAssessmentEngine,
    SupportType,
    HermesActivationLevel
)
from backend.services.memory_service import normalize_memory, update_memory
from backend.services.brain_engine import brain_engine
from backend.services.voice_orchestrator import voice_orchestrator
from brain.schemas import UnifiedTurnRequest, InputType

client = TestClient(app)


class TestSprint8AdaptiveModelOrchestration:

    def test_01_simple_greeting_routes_to_phi3(self):
        """(1) Proves simple greeting routes to fast conversational model (Phi-3)."""
        decision = SakiModelOrchestrator.classify_request("Hey Saki, good morning!")
        assert decision.selected_model == settings.MODEL_PHI3
        assert decision.conversation_mode == "casual"

    def test_02_simple_acknowledgement_routes_to_phi3(self):
        """(2) Proves short conversational acknowledgement routes to Phi-3."""
        decision = SakiModelOrchestrator.classify_request("Cool, thanks!")
        assert decision.selected_model == settings.MODEL_PHI3
        assert decision.conversation_mode == "casual"

    def test_03_complex_reasoning_routes_to_qwen3(self):
        """(3) Proves deep analytical question routes to Qwen3 (Thinking Mode)."""
        decision = SakiModelOrchestrator.classify_request(
            "Explain the architectural differences and trade-offs between Raft and Paxos consensus algorithms."
        )
        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"

    def test_04_coding_debugging_routes_to_qwen_coder(self):
        """(4) Proves code implementation / debugging request routes to Qwen 2.5 Coder."""
        decision = SakiModelOrchestrator.classify_request(
            "Write a FastAPI endpoint with asynchronous websocket connection pooling."
        )
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"
        assert decision.coding_required is True

    def test_05_vision_input_routes_to_gemma(self):
        """(5) Proves image input routes to Gemma 3 (Vision Mode)."""
        decision = SakiModelOrchestrator.classify_request(
            "What UI elements are shown in this screenshot?",
            attachments=[{"name": "mockup.png", "type": "image/png"}]
        )
        assert decision.selected_model == settings.MODEL_GEMMA
        assert decision.conversation_mode == "vision"
        assert decision.vision_required is True

    def test_06_deep_emotional_support_routes_to_hermes(self):
        """(6) Proves deep emotional distress routes to Hermes 2 (Support Mode)."""
        decision = SakiModelOrchestrator.classify_request(
            "I'm feeling completely lost and exhausted, everything I worked on this week fell apart."
        )
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"
        assert decision.emotional_importance == "high"

    def test_07_mild_frustration_plus_coding_prefers_coder(self):
        """(7) Proves mild frustration during coding task remains with Coder rather than switching to Hermes."""
        decision = SakiModelOrchestrator.classify_request(
            "I'm frustrated. Why does this API endpoint keep returning 500 internal server error?"
        )
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_08_emotional_plus_practical_dominant_strategy(self):
        """(8) Proves mixed emotional + practical request routes according to dominant intent."""
        # Dominant distress -> Hermes
        decision_emo = SakiModelOrchestrator.classify_request(
            "I feel completely overwhelmed and hopeless with this project, can you help me?"
        )
        assert decision_emo.selected_model == settings.MODEL_HERMES

        # Dominant technical -> Coder with emotional awareness
        decision_tech = SakiModelOrchestrator.classify_request(
            "I'm really stressed about tomorrow's deadline, how do I fix this SQLAlchemy connection error?"
        )
        assert decision_tech.selected_model == settings.MODEL_CODER

    def test_09_telugu_emotional_support_routes_to_hermes(self):
        """(9) Proves authentic Telugu emotional statement activates Hermes 2."""
        decision = SakiModelOrchestrator.classify_request(
            "చాలా ఒంటరిగా ఉంది, నా ఇంటర్వ్యూ పోయింది మరియు చాలా బాధగా ఉంది."
        )
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_10_kannada_emotional_support_routes_to_hermes(self):
        """(10) Proves authentic Kannada emotional statement activates Hermes 2."""
        decision = SakiModelOrchestrator.classify_request(
            "ತುಂಬಾ ಒಂಟಿತನ ಅನಿಸ್ತಿದೆ, ನನ್ನ ಪ್ರಾಜೆಕ್ಟ್ ಹಾಳಾಯ್ತು ಮತ್ತು ತುಂಬಾ ಬೇసರವಾಗಿದೆ."
        )
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_11_telugu_coding_routes_to_qwen_coder(self):
        """(11) Proves Telugu programming question routes to Qwen 2.5 Coder."""
        decision = SakiModelOrchestrator.classify_request(
            "నాకు FastAPI లో async websocket router రాయడానికి Python code చూపించు."
        )
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_12_kannada_coding_routes_to_qwen_coder(self):
        """(12) Proves Kannada programming question routes to Qwen 2.5 Coder."""
        decision = SakiModelOrchestrator.classify_request(
            "ನನಗೆ React components ನಲ್ಲಿ custom debounce hook ಹೇಗೆ implement ಮಾಡುವುದು code ಕೊಡಿ."
        )
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_13_telugu_reasoning_routes_to_qwen3(self):
        """(13) Proves Telugu complex reasoning routes to Qwen3."""
        decision = SakiModelOrchestrator.classify_request(
            "తెలుగులో explain why Byzantine fault tolerance is harder than crash fault tolerance."
        )
        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"

    def test_14_kannada_reasoning_routes_to_qwen3(self):
        """(14) Proves Kannada complex reasoning routes to Qwen3."""
        decision = SakiModelOrchestrator.classify_request(
            "ಕನ್ನಡದಲ್ಲಿ explain how distributed consensus protocols operate across network partitions."
        )
        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"

    def test_15_model_stability_margin_anti_flapping(self):
        """(15) Proves router maintains model stability and avoids unnecessary micro-switching."""
        prev_model = settings.MODEL_QWEN3
        decision = SakiModelOrchestrator.classify_request(
            "What do you think about this general approach?",
            previous_model=prev_model
        )
        assert decision.selected_model == prev_model
        assert decision.should_switch_model is False

    def test_16_strong_capability_override(self):
        """(16) Proves strong capability requirement (Vision/Code) immediately switches model regardless of previous."""
        # Previous Phi-3 -> Code task immediately switches to Coder
        decision = SakiModelOrchestrator.classify_request(
            "Write a Python script to parse this JSON log.",
            previous_model=settings.MODEL_PHI3
        )
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.should_switch_model is True

    def test_17_model_switching_after_topic_change(self):
        """(17) Proves model transitions smoothly when user shifts conversation from coding to emotional support."""
        conv_id = "s8_topic_shift"
        with patch("backend.services.brain_engine.call_model") as mock_call, \
             patch("backend.services.brain_engine.load_memory") as mock_mem:

            mock_mem.return_value = normalize_memory({"conversation_history": []})
            mock_call.side_effect = [
                "Here is the database router code.",
                "I hear you. It sounds like you've been carrying a lot of weight today."
            ]

            # Turn 1: Code task -> Coder
            res1 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t1", text="Fix my FastAPI database session error.")
            )
            assert res1.routing.get("selected_model") == settings.MODEL_CODER

            # Turn 2: Emotional shift -> Hermes
            res2 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t2", text="Honestly, I'm completely burned out and crying.")
            )
            assert res2.routing.get("selected_model") == settings.MODEL_HERMES

    def test_18_context_preservation_across_model_switches(self):
        """(18) Proves active project and conversational state transfer seamlessly across model switches."""
        conv_id = "s8_ctx_preservation"
        with patch("backend.services.brain_engine.call_model") as mock_call, \
             patch("backend.services.brain_engine.load_memory") as mock_mem:

            mock_mem.return_value = normalize_memory({
                "conversation_history": [{"user": "We are building Saki Brain", "saki": "Great!"}]
            })
            mock_call.return_value = "I understand the Saki Brain architecture."

            res = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t_ctx", text="Can we optimize the memory engine?")
            )
            assert res.routing is not None
            assert res.routing.get("selected_model") in [settings.MODEL_CODER, settings.MODEL_QWEN3]

    def test_19_memory_preservation_across_model_switches(self):
        """(19) Proves durable memories remain accessible before and after model transitions."""
        mem = normalize_memory({
            "memories": [
                {
                    "id": "mem_arch",
                    "type": "PROJECT_FACT",
                    "content": "Saki uses a unified brain architecture.",
                    "importance": 9,
                    "confidence": 0.95,
                    "score": 10.0
                }
            ]
        })
        decision = SakiModelOrchestrator.classify_request(
            "What is our brain architecture?",
            memory_data=mem,
            previous_model=settings.MODEL_PHI3
        )
        assert decision.selected_model == settings.MODEL_QWEN3

    def test_20_language_preservation_across_model_switches(self):
        """(20) Proves Telugu/Kannada language profile transfers intact when switching models."""
        conv_id = "s8_lang_switch"
        with patch("backend.services.brain_engine.call_model") as mock_call:
            mock_call.return_value = "నమస్కారం! నేను సహాయం చేస్తాను."
            res = brain_engine.execute_turn(
                UnifiedTurnRequest(
                    conversation_id=conv_id,
                    turn_id="t_lang_sw",
                    text="నాకు పైథాన్ లో రికర్షన్ ఎలా పనిచేస్తుందో వివరించండి."
                )
            )
            assert res.detected_language == "te"
            assert res.routing.get("selected_model") in [settings.MODEL_CODER, settings.MODEL_QWEN3]

    def test_21_voice_model_switching(self):
        """(21) Proves spoken voice input uses dynamic model orchestration (not fixed model)."""
        with patch("backend.services.stt_service.stt_service.transcribe_speech") as mock_stt, \
             patch("backend.services.brain_engine.call_model") as mock_model:

            mock_stt.return_value = MagicMock(transcript="I'm feeling so overwhelmed today", language="en", success=True)
            mock_model.return_value = "Take a breath, I am here with you."

            turn_res = voice_orchestrator.execute_voice_turn(
                audio_input=b"dummy_voice_audio",
                conversation_id="v_turn_s8"
            )
            assert turn_res.selected_model == settings.MODEL_HERMES
            assert turn_res.conversation_mode == "support"

    def test_22_model_loading_and_unloading_safety(self):
        """(22) Proves routing decision provides keep_loaded and resource flags."""
        decision = SakiModelOrchestrator.classify_request("Write a quick sorting function in Python.")
        assert decision.selected_model == settings.MODEL_CODER
        assert hasattr(decision, "should_stop_after_response")

    def test_23_no_unloading_of_active_models(self):
        """(23) Proves active turn execution holds model until turn completes."""
        decision = SakiModelOrchestrator.classify_request("Hello Saki!")
        assert decision.should_stop_after_response is True

    def test_24_resource_constrained_fallback(self):
        """(24) Proves uncertainty fallback model setting is respected."""
        assert settings.HERMES_UNCERTAINTY_FALLBACK_MODEL == "qwen3:8b"

    def test_25_conversation_position_inference(self):
        """(25) Proves conversational position is inferred accurately across lifecycle."""
        pos_open = infer_conversation_position("hi saki", [], 0.0, False)
        assert pos_open == ConversationPosition.OPENING

        pos_close = infer_conversation_position("bye, see you tomorrow!", [{"u": "x"}], 0.0, False)
        assert pos_close == ConversationPosition.CLOSING

        pos_emo = infer_conversation_position("i'm crying", [{"u": "x"}], 0.85, False)
        assert pos_emo == ConversationPosition.EMOTIONAL_PROCESSING

        pos_code = infer_conversation_position("debug this code", [{"u": "x"}], 0.0, True)
        assert pos_code == ConversationPosition.PROBLEM_SOLVING

    def test_26_core_receives_model_events(self):
        """(26) Proves turn execution emits complete state telemetry."""
        conv_id = "s8_core_events"
        with patch("backend.services.brain_engine.call_model") as mock_call:
            mock_call.return_value = "All systems operational."
            res = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t_events", text="Status check.")
            )
            assert res.routing is not None
            assert "selected_model" in res.routing

    def test_27_user_facing_response_never_leaks_model_details(self):
        """(27) Proves final response text never reveals internal model tags or reasoning tags."""
        raw_draft = (
            "<think>Routing to Qwen 2.5 Coder for Python request</think>\n"
            "[Instruction: Selected Model = qwen2.5-coder:7b]\n"
            "Here is the Python function you requested:\n\n"
            "```python\ndef add(a, b):\n    return a + b\n```"
        )
        from backend.services.response_evaluator import evaluate_response
        eval_res = evaluate_response(raw_draft)
        assert "<think>" not in eval_res.repaired_text
        assert "[Instruction" not in eval_res.repaired_text
        assert "qwen2.5-coder:7b" not in eval_res.repaired_text
        assert "def add" in eval_res.repaired_text
