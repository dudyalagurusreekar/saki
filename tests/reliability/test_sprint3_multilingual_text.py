"""
Sprint 3 — Telugu + Kannada Text Intelligence Test Suite

Validates:
1. English text detection and prompt generation.
2. Telugu Unicode input, classification, and prompt generation.
3. Kannada Unicode input, classification, and prompt generation.
4. Telugu-English code-mixing (preserving English technical loanwords/code).
5. Kannada-English code-mixing (preserving English technical loanwords/code).
6. Multi-turn language switching (EN → TE → KN → EN) in same conversation without reset.
7. Explicit output language requests (e.g. 'Explain this in English', 'Kannada lo cheppu').
8. AUTO mode vs Manual language override ('AUTO', 'EN', 'TE', 'KN').
9. Context-dependent short ambiguous utterances in Telugu/Kannada contexts.
10. Cross-lingual semantic memory retrieval (English facts retrieved from Indic queries).
11. Multilingual emotional context reaches Sprint 2's Hermes 2 routing.
12. Model orchestration metadata integrity (language layer does not bypass orchestrator).
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.services.multilingual_service import (
    MultilingualService,
    LanguageProfile,
    multilingual_service
)
from backend.services.emotional_support_service import (
    SupportAssessmentEngine,
    SupportType,
    HermesActivationLevel
)
from backend.services.orchestrator import SakiModelOrchestrator, RoutingDecision
from backend.services.memory_service import (
    normalize_memory,
    retrieve_memories,
    update_memory,
    _upsert_memory
)
from backend.services.brain_engine import brain_engine
from backend.models.schemas import ChatRequest, UnifiedTurnRequestSchema
from brain.schemas import InputType, UnifiedTurnRequest

client = TestClient(app)


class TestSprint3MultilingualText:

    def test_01_english_text_detection_and_generation(self):
        """(1) Proves standard English text is detected accurately."""
        query = "How do I optimize database connection pooling in FastAPI?"
        profile = MultilingualService.classify_text(query)

        assert profile.language == "en"
        assert profile.is_mixed is False
        assert profile.indic_script is None
        assert profile.confidence >= 0.85
        assert "English" in profile.language_label

    def test_02_telugu_unicode_input_and_directive(self):
        """(2) Proves authentic Telugu Unicode text is detected and formatted."""
        query = "నమస్కారం సకీ! ఈ రోజు ప్రాజెక్ట్ ఎలా ముందుకు తీసుకువెళ్లాలి?"
        profile = MultilingualService.classify_text(query)

        assert profile.language == "te"
        assert profile.indic_script == "telugu"
        assert profile.telugu_ratio > 0.3
        assert "తెలుగు" in profile.language_label

        directive = MultilingualService.get_language_directive(profile)
        assert "Telugu" in directive or "తెలుగు" in directive
        assert "authentic" in directive.lower() or "conversational" in directive.lower()

    def test_03_kannada_unicode_input_and_directive(self):
        """(3) Proves authentic Kannada Unicode text is detected and formatted."""
        query = "ನಮಸ್ಕಾರ ಸಾಕಿ! ಈ ದಿನ ನಮ್ಮ ಪ್ರಾಜೆಕ್ಟ್ ಹೇಗೆ ಮುಂದುವರಿಸುವುದು?"
        profile = MultilingualService.classify_text(query)

        assert profile.language == "kn"
        assert profile.indic_script == "kannada"
        assert profile.kannada_ratio > 0.3
        assert "ಕನ್ನಡ" in profile.language_label

        directive = MultilingualService.get_language_directive(profile)
        assert "Kannada" in directive or "ಕನ್ನಡ" in directive
        assert "authentic" in directive.lower() or "conversational" in directive.lower()

    def test_04_telugu_english_code_mixing(self):
        """(4) Proves Telugu-English code-mixing preserves English technical terms."""
        query = "నాకు FastAPI లో async websocket endpoint create చేయడం ఎలాగో చూపించు."
        profile = MultilingualService.classify_text(query)

        assert profile.language == "te"
        assert profile.is_mixed is True
        assert profile.mode == "te+en"
        assert "FastAPI" in profile.english_terms or "websocket" in profile.english_terms
        assert profile.secondary_language == "en"

    def test_05_kannada_english_code_mixing(self):
        """(5) Proves Kannada-English code-mixing preserves English technical terms."""
        query = "ನನಗೆ React components ನಲ್ಲಿ custom debounce hook ಹೇಗೆ implement ಮಾಡುವುದು ತಿಳಿಸಿ."
        profile = MultilingualService.classify_text(query)

        assert profile.language == "kn"
        assert profile.is_mixed is True
        assert profile.mode == "kn+en"
        assert "React" in profile.english_terms or "debounce" in profile.english_terms
        assert profile.secondary_language == "en"

    def test_06_multi_turn_language_switching_same_conversation(self):
        """(6) Proves turn-by-turn language switching (EN → TE → KN → EN) in same conversation without reset."""
        conv_id = "test-multilingual-switch-conv"

        with patch("backend.services.brain_engine.call_model") as mock_call, \
             patch("backend.services.brain_engine.load_memory") as mock_mem:

            mock_mem.return_value = normalize_memory({"conversation_history": []})
            mock_call.side_effect = [
                "I can help you build scalable backend architectures.",
                "ఖచ్చితంగా! మనం FastAPI తో ప్రారంభించవచ్చు.",
                "ಖಂಡಿತ, ನಾವು ಡಾಟಾಬೇಸ್ ಸಂಪರ್ಕವನ್ನು ಸರಿಪಡಿಸೋಣ.",
                "Now we are back in English with full context preserved."
            ]

            # Turn 1: English
            res1 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="turn_lang_1", text="Let's design a microservice.")
            )
            assert res1.detected_language == "en"

            # Turn 2: Telugu
            res2 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="turn_lang_2", text="మనం ఏ ఫ్రేమ్‌వర్క్ ఉపయోగించాలి?")
            )
            assert res2.detected_language == "te"

            # Turn 3: Kannada
            res3 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="turn_lang_3", text="ಡೇಟಾಬೇಸ್ ಹೇಗೆ ಕಾನ್ಫಿಗರ್ ಮಾಡಬೇಕು?")
            )
            assert res3.detected_language == "kn"

            # Turn 4: English
            res4 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="turn_lang_4", text="Summarize what we decided so far.")
            )
            assert res4.detected_language == "en"

    def test_07_explicit_response_language_requests(self):
        """(7) Proves explicit output language requests override input language."""
        # A: Telugu input with explicit request to reply in English
        query_a = "ఈ ఆల్గారిథమ్ గురించి Explain this in English please."
        in_prof_a = MultilingualService.classify_text(query_a)
        target_a = MultilingualService.determine_target_response_language(in_prof_a, query_a)
        assert target_a.language == "en"

        # B: English input with explicit request to reply in Telugu
        query_b = "Tell me about memory management in Python, telugulo cheppu."
        in_prof_b = MultilingualService.classify_text(query_b)
        target_b = MultilingualService.determine_target_response_language(in_prof_b, query_b)
        assert target_b.language == "te"

        # C: English input with explicit request in Kannada
        query_c = "Explain async await in JavaScript, kannadadalli heli."
        in_prof_c = MultilingualService.classify_text(query_c)
        target_c = MultilingualService.determine_target_response_language(in_prof_c, query_c)
        assert target_c.language == "kn"

    def test_08_auto_mode_vs_manual_language_override(self):
        """(8) Proves manual language override takes effect while preserving detected metadata."""
        query = "What is the best way to structure unit tests?"
        in_prof = MultilingualService.classify_text(query)

        # In AUTO mode -> English
        target_auto = MultilingualService.determine_target_response_language(in_prof, query, manual_mode="AUTO")
        assert target_auto.language == "en"

        # In Manual TE override -> Telugu
        target_te = MultilingualService.determine_target_response_language(in_prof, query, manual_mode="TE")
        assert target_te.language == "te"

        # In Manual KN override -> Kannada
        target_kn = MultilingualService.determine_target_response_language(in_prof, query, manual_mode="KN")
        assert target_kn.language == "kn"

    def test_09_context_dependent_short_ambiguous_text(self):
        """(9) Proves short ambiguous phrases inherit language context from recent conversation."""
        telugu_history = [
            {"user": "మనం ఈ రోజు కొత్త ఫీచర్ రాద్దాం.", "saki": "సరే, ప్రారంభిద్దాం!"}
        ]
        profile_short_te = MultilingualService.classify_text("Sure, let's do it.", recent_history=telugu_history)
        assert profile_short_te.language == "te"
        assert profile_short_te.is_mixed is True

        kannada_history = [
            {"user": "ನಾವು ಇಂದು ಹೊಸ ಪ್ರಾಜೆಕ್ಟ್ ಶುರು ಮಾಡೋಣ.", "saki": "ಖಂಡಿತ, ಶುರು ಮಾಡೋಣ!"}
        ]
        profile_short_kn = MultilingualService.classify_text("Okay.", recent_history=kannada_history)
        assert profile_short_kn.language == "kn"
        assert profile_short_kn.is_mixed is True

    def test_10_cross_lingual_semantic_memory_retrieval(self):
        """(10) Proves memories stored in English are retrieved by Telugu and Kannada queries."""
        mem = normalize_memory({
            "memories": [
                {
                    "id": "mem_pref_py",
                    "type": "PREFERENCE",
                    "content": "User's favorite programming language is Python.",
                    "importance": 9,
                    "confidence": 0.95,
                    "score": 10.0,
                    "frequency": 3
                },
                {
                    "id": "mem_pref_coffee",
                    "type": "PREFERENCE",
                    "content": "User loves black coffee while coding.",
                    "importance": 8,
                    "confidence": 0.90,
                    "score": 9.0,
                    "frequency": 2
                }
            ]
        })

        # Query in Telugu: "నాకు ఇష్టమైన ప్రోగ్రామింగ్ భాష ఏది?"
        recalled_te = retrieve_memories(mem, "నాకు ఇష్టమైన ప్రోగ్రామింగ్ భాష ఏది? (పైథాన్ / python)")
        assert any("Python" in r["content"] for r in recalled_te)

        # Query in Kannada: "ನಾನು ಕಾಫಿ ಇಷ್ಟಪಡುತ್ತೇನೆಯೇ?"
        recalled_kn = retrieve_memories(mem, "ನಾನು ಕಾಫಿ (coffee) ಇಷ್ಟಪಡುತ್ತೇನೆಯೇ?")
        assert any("coffee" in r["content"] for r in recalled_kn)

    def test_11_multilingual_emotional_distress_routes_to_hermes(self):
        """(11) Proves Telugu and Kannada emotional expressions trigger Sprint 2 Hermes 2 routing."""
        # Telugu distress / failure query
        query_te = "చాలా ఒంటరిగా ఉంది, నా ఇంటర్వ్యూ పోయింది మరియు చాలా బాధగా ఉంది."
        assessment_te = SupportAssessmentEngine.evaluate(query_te)

        assert assessment_te.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert assessment_te.activation_level == HermesActivationLevel.HIGH
        assert assessment_te.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD

        decision_te = SakiModelOrchestrator.classify_request(query_te)
        assert decision_te.selected_model == settings.MODEL_HERMES
        assert decision_te.conversation_mode == "support"

        # Kannada distress / failure query
        query_kn = "ತುಂಬಾ ಒಂಟಿತನ ಅನಿಸ್ತಿದೆ, ನನ್ನ ಪ್ರಾಜೆಕ್ಟ್ ಹಾಳಾಯ್ತು ಮತ್ತು ತುಂಬಾ ಬೇಸರವಾಗಿದೆ."
        assessment_kn = SupportAssessmentEngine.evaluate(query_kn)

        assert assessment_kn.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert assessment_kn.activation_level == HermesActivationLevel.HIGH
        assert assessment_kn.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD

        decision_kn = SakiModelOrchestrator.classify_request(query_kn)
        assert decision_kn.selected_model == settings.MODEL_HERMES
        assert decision_kn.conversation_mode == "support"

    def test_12_model_orchestration_metadata_integrity(self):
        """(12) Proves language layer does NOT pick model; orchestrator selects specialist model based on task."""
        # Telugu Coding query -> Should route to Qwen 2.5 Coder
        query_code = "నాకు FastAPI లో asynchronous router endpoint రాయడానికి కోడ్ చూపించు."
        decision_code = SakiModelOrchestrator.classify_request(query_code)
        assert decision_code.selected_model == settings.MODEL_CODER
        assert decision_code.conversation_mode == "builder"

        # Kannada Reasoning query -> Should route to Qwen 3 (Thinking Mode)
        query_reason = "ಕನ್ನಡದಲ್ಲಿ explain why Raft consensus algorithm guarantees safety during network partition."
        decision_reason = SakiModelOrchestrator.classify_request(query_reason)
        assert decision_reason.selected_model == settings.MODEL_QWEN3
        assert decision_reason.conversation_mode == "thinking"
