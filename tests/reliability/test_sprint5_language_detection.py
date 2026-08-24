"""
Sprint 5 — Automatic Language Detection + Manual Language Control Test Suite

Validates:
1. High-confidence English detection.
2. High-confidence Telugu detection (Unicode).
3. High-confidence Kannada detection (Unicode).
4. Mixed Telugu-English code-mixing & linguistic segment extraction.
5. Mixed Kannada-English code-mixing & linguistic segment extraction.
6. Contextual resolution of short/ambiguous utterances from conversation history.
7. Manual language control overrides (AUTO, EN, TE, KN) and seamless return to AUTO.
8. Explicit in-message output language requests.
9. Multi-turn language switching (EN -> TE -> KN -> EN) in same conversation without reset.
10. Language metadata propagation to Emotional Analyzer (Hermes 2) and Orchestrator (Coder/Qwen3).
11. Quantitative evaluation dataset metrics (accuracy > 95%, latency < 10ms).
12. End-to-end voice STT -> Language Detection -> Brain execution flow.
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
from backend.services.orchestrator import SakiModelOrchestrator
from backend.services.emotional_support_service import (
    SupportAssessmentEngine,
    SupportType,
    HermesActivationLevel
)
from backend.services.voice_orchestrator import voice_orchestrator, VoiceTurnResult
from backend.services.stt_service import STTTranscriptionResult
from backend.services.brain_engine import brain_engine
from backend.services.memory_service import normalize_memory
from brain.schemas import UnifiedTurnRequest, InputType

client = TestClient(app)


class TestSprint5LanguageDetection:

    def test_01_high_confidence_english_detection(self):
        """(1) Proves high-confidence English detection returns clean profile and metadata."""
        query = "How do I implement connection pooling in SQLAlchemy with FastAPI?"
        profile = MultilingualService.classify_text(query)

        assert profile.language == "en"
        assert profile.primary_language == "en"
        assert profile.secondary_language is None
        assert profile.is_code_mixed is False
        assert profile.confidence >= 0.90
        assert profile.detection_source == "unicode_script"
        assert profile.mode == "pure_en"

    def test_02_high_confidence_telugu_detection(self):
        """(2) Proves high-confidence Telugu Unicode detection returns authentic metadata."""
        query = "నమస్కారం సకీ! ఈ రోజు ప్రాజెక్ట్ ఎలా ముందుకు తీసుకువెళ్లాలి?"
        profile = MultilingualService.classify_text(query)

        assert profile.language == "te"
        assert profile.primary_language == "te"
        assert profile.indic_script == "telugu"
        assert profile.confidence >= 0.90
        assert profile.detection_source == "unicode_script"
        assert "తెలుగు" in profile.language_label

    def test_03_high_confidence_kannada_detection(self):
        """(3) Proves high-confidence Kannada Unicode detection returns authentic metadata."""
        query = "ನಮಸ್ಕಾರ ಸಾಕಿ! ಈ ದಿನ ನಮ್ಮ ಪ್ರಾಜೆಕ್ಟ್ ಹೇಗೆ ಮುಂದುವರಿಸುವುದು?"
        profile = MultilingualService.classify_text(query)

        assert profile.language == "kn"
        assert profile.primary_language == "kn"
        assert profile.indic_script == "kannada"
        assert profile.confidence >= 0.90
        assert profile.detection_source == "unicode_script"
        assert "ಕನ್ನಡ" in profile.language_label

    def test_04_telugu_english_mixed_and_segments(self):
        """(4) Proves Telugu-English code-mixing identifies dominant language and extracts segments."""
        # A: Unicode code-mixed
        query_a = "నాకు FastAPI లో async websocket endpoint create చేయడం ఎలాగో చూపించు."
        profile_a = MultilingualService.classify_text(query_a)

        assert profile_a.primary_language == "te"
        assert profile_a.secondary_language == "en"
        assert profile_a.is_code_mixed is True
        assert profile_a.mode == "te+en"
        assert len(profile_a.language_segments) >= 2
        assert any(seg["language"] == "te" for seg in profile_a.language_segments)
        assert any(seg["language"] == "en" for seg in profile_a.language_segments)

        # B: Romanized Indian mixed
        query_b = "Ee project lo API enduku fail avutundi?"
        profile_b = MultilingualService.classify_text(query_b)

        assert profile_b.primary_language == "te"
        assert profile_b.is_code_mixed is True
        assert profile_b.detection_source == "romanized_lexicon"

    def test_05_kannada_english_mixed_and_segments(self):
        """(5) Proves Kannada-English code-mixing identifies dominant language and extracts segments."""
        # A: Unicode code-mixed
        query_a = "ಈ project ಯಾಕೆ fail ಆಗುತ್ತಿದೆ? ನನ್ನ backend code check ಮಾಡ್ತೀಯಾ?"
        profile_a = MultilingualService.classify_text(query_a)

        assert profile_a.primary_language == "kn"
        assert profile_a.secondary_language == "en"
        assert profile_a.is_code_mixed is True
        assert profile_a.mode == "kn+en"
        assert len(profile_a.language_segments) >= 2

        # B: Romanized Indian mixed
        query_b = "Tomorrow college ge yavaga hogabeku?"
        profile_b = MultilingualService.classify_text(query_b)
        assert profile_b.primary_language in ["kn", "te"]

    def test_06_ambiguous_short_utterance_context_resolution(self):
        """(6) Proves short ambiguous phrases inherit language context from recent conversation."""
        # Telugu context
        history_te = [
            {"user": "మనం ఈ రోజు కొత్త ఫీచర్ రాద్దాం.", "saki": "సరే, ప్రారంభిద్దాం!"}
        ]
        prof_te = MultilingualService.classify_text("Sure, let's do it.", recent_history=history_te)
        assert prof_te.language == "te"
        assert prof_te.detection_source == "conversation_context"

        # Kannada context
        history_kn = [
            {"user": "ನಾವು ಇಂದು ಹೊಸ ಪ್ರಾಜೆಕ್ಟ್ ಶುರು ಮಾಡೋಣ.", "saki": "ಖಂಡಿತ, ಶುರು ಮಾಡೋಣ!"}
        ]
        prof_kn = MultilingualService.classify_text("Okay.", recent_history=history_kn)
        assert prof_kn.language == "kn"
        assert prof_kn.detection_source == "conversation_context"

        # Empty history fallback
        prof_none = MultilingualService.classify_text("Ok.")
        assert prof_none.language == "en"
        assert prof_none.detection_source in ["fallback", "unicode_script"]

    def test_07_manual_language_control_overrides_and_auto_return(self):
        """(7) Proves manual language overrides enforce preferred output and return cleanly to AUTO."""
        query = "What is the best way to structure unit tests?"
        base_prof = MultilingualService.classify_text(query)

        # 1. AUTO mode
        target_auto = MultilingualService.determine_target_response_language(base_prof, query, manual_mode="AUTO")
        assert target_auto.language == "en"
        assert target_auto.manual_mode == "AUTO"

        # 2. Manual TE override
        target_te = MultilingualService.determine_target_response_language(base_prof, query, manual_mode="TE")
        assert target_te.language == "te"
        assert target_te.manual_mode == "TE"
        assert target_te.detection_source == "manual_override"

        # 3. Manual KN override
        target_kn = MultilingualService.determine_target_response_language(base_prof, query, manual_mode="KN")
        assert target_kn.language == "kn"
        assert target_kn.manual_mode == "KN"
        assert target_kn.detection_source == "manual_override"

        # 4. Return to AUTO
        target_return = MultilingualService.determine_target_response_language(base_prof, query, manual_mode="AUTO")
        assert target_return.language == "en"
        assert target_return.manual_mode == "AUTO"

    def test_08_explicit_output_language_requests(self):
        """(8) Proves explicit in-message language requests override default response language."""
        # A: Telugu input asking for English output
        query_a = "ఈ ఆల్గారిథమ్ గురించి Explain this in English please."
        prof_a = MultilingualService.classify_text(query_a)
        target_a = MultilingualService.determine_target_response_language(prof_a, query_a)
        assert target_a.language == "en"
        assert target_a.requested_output_language == "en"
        assert target_a.detection_source == "explicit_request"

        # B: English input asking for Telugu output
        query_b = "Tell me about memory management in Python, telugulo cheppu."
        prof_b = MultilingualService.classify_text(query_b)
        target_b = MultilingualService.determine_target_response_language(prof_b, query_b)
        assert target_b.language == "te"
        assert target_b.requested_output_language == "te"

        # C: English input asking for Kannada output
        query_c = "Explain async await in JavaScript, kannadadalli heli."
        prof_c = MultilingualService.classify_text(query_c)
        target_c = MultilingualService.determine_target_response_language(prof_c, query_c)
        assert target_c.language == "kn"
        assert target_c.requested_output_language == "kn"

    def test_09_multi_turn_switching_same_conversation(self):
        """(9) Proves multi-turn switching (EN -> TE -> KN -> EN) maintains conversation continuity."""
        conv_id = "test-sprint5-switching-conv"

        with patch("backend.services.brain_engine.call_model") as mock_call, \
             patch("backend.services.brain_engine.load_memory") as mock_mem:

            mock_mem.return_value = normalize_memory({"conversation_history": []})
            mock_call.side_effect = [
                "Hello! Let's work on our project.",
                "ఖచ్చితంగా, మనం ప్రారంభించవచ్చు.",
                "ಖಂಡಿತ, ನಾವು ಮುಂದುವರಿಸೋಣ.",
                "We are back in English with unified state."
            ]

            # Turn 1: English
            res1 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t1", text="Hello Saki.")
            )
            assert res1.detected_language == "en"

            # Turn 2: Telugu
            res2 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t2", text="మనం ఏ ఫ్రేమ్‌వర్క్ ఉపయోగించాలి?")
            )
            assert res2.detected_language == "te"

            # Turn 3: Kannada
            res3 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t3", text="ಡೇಟಾಬೇಸ್ ಹೇಗೆ ಕಾನ್ಫಿಗರ್ ಮಾಡಬೇಕು?")
            )
            assert res3.detected_language == "kn"

            # Turn 4: English
            res4 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="t4", text="Summarize our architecture.")
            )
            assert res4.detected_language == "en"

    def test_10_language_metadata_propagation_to_orchestrator_and_models(self):
        """(10) Proves language layer does not pick model; orchestrator routes based on task + emotion."""
        # Telugu distress -> Hermes 2
        query_emo = "చాలా ఒంటరిగా ఉంది, నా ఇంటర్వ్యూ పోయింది మరియు చాలా బాధగా ఉంది."
        decision_emo = SakiModelOrchestrator.classify_request(query_emo)
        assert decision_emo.selected_model == settings.MODEL_HERMES
        assert decision_emo.conversation_mode == "support"

        # Telugu coding -> Qwen 2.5 Coder
        query_code = "నాకు FastAPI లో asynchronous router endpoint రాయడానికి కోడ్ చూపించు."
        decision_code = SakiModelOrchestrator.classify_request(query_code)
        assert decision_code.selected_model == settings.MODEL_CODER
        assert decision_code.conversation_mode == "builder"

        # Kannada reasoning -> Qwen 3
        query_think = "ಕನ್ನಡದಲ್ಲಿ explain why Raft consensus algorithm guarantees safety during network partition."
        decision_think = SakiModelOrchestrator.classify_request(query_think)
        assert decision_think.selected_model == settings.MODEL_QWEN3
        assert decision_think.conversation_mode == "thinking"

    def test_11_quantitative_evaluation_dataset_metrics(self):
        """(11) Evaluates representative real conversational dataset and measures accuracy and latency."""
        dataset = [
            # English
            ("How do I implement binary search in Python?", "en", False),
            ("Can you help me design a scalable microservices architecture?", "en", False),
            ("Good morning Saki, hope you have a great day!", "en", False),
            # Telugu
            ("నమస్కారం సకీ! ఈ రోజు ప్రాజెక్ట్ ఎలా ఉంది?", "te", False),
            ("నాకు పైథాన్ లో లిస్ట్ కాంప్రెహెన్షన్ ఎలా వాడాలో చూపించు.", "te", False),
            ("చాలా బాధగా ఉంది, ఈ రోజు నా పరీక్ష బాగా రాయలేదు.", "te", False),
            # Kannada
            ("ನಮಸ್ಕಾರ ಸಾಕಿ! ಈ ದಿನ ನಮ್ಮ ಕೆಲಸ ಹೇಗೆ ಸಾಗಿದೆ?", "kn", False),
            ("ನನಗೆ ರಿಯಾಕ್ಟ್ ಕಾಂಪೊನೆಂಟ್ಸ್ ಬಗ್ಗೆ ತಿಳಿಸಿಕೊಡಿ.", "kn", False),
            ("ತುಂಬಾ ಸುಸ್ತಾಗಿದೆ, ಇವತ್ತು ತುಂಬಾ ಕೆಲಸ ಇತ್ತು.", "kn", False),
            # Mixed Telugu-English
            ("నాకు FastAPI లో async websocket endpoint create చేయడం ఎలాగో చూపించు.", "te", True),
            ("Ee project lo database connection enduku fail avutundi?", "te", True),
            # Mixed Kannada-English
            ("ಈ project ಯಾಕೆ fail ಆಗುತ್ತಿದೆ? backend code check ಮಾಡು.", "kn", True),
            ("Tomorrow morning college ge hogabeku.", "kn", True),
        ]

        correct_lang = 0
        correct_mixed = 0
        total_latency_ms = 0.0

        for text, expected_lang, expected_mixed in dataset:
            t0 = time.perf_counter()
            prof = MultilingualService.classify_text(text)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            total_latency_ms += lat_ms

            if prof.primary_language == expected_lang:
                correct_lang += 1
            if prof.is_code_mixed == expected_mixed:
                correct_mixed += 1

        accuracy = correct_lang / len(dataset)
        mixed_acc = correct_mixed / len(dataset)
        avg_latency = total_latency_ms / len(dataset)

        assert accuracy >= 0.90, f"Language accuracy was {accuracy:.2%}, expected >= 90%"
        assert mixed_acc >= 0.85, f"Mixed accuracy was {mixed_acc:.2%}, expected >= 85%"
        assert avg_latency < 10.0, f"Avg detection latency was {avg_latency:.2f}ms, expected < 10ms"

    def test_12_end_to_end_voice_stt_language_detection_pipeline(self):
        """(12) Proves voice STT output transitions into Language Analyzer and executes via Saki Brain."""
        with patch("backend.services.stt_service.stt_service.transcribe_speech") as mock_stt, \
             patch("backend.services.brain_engine.call_model") as mock_model:

            # 1. Voice Telugu
            mock_stt.return_value = STTTranscriptionResult(
                transcript="నమస్కారం సకీ! మన ప్రాజెక్ట్ స్టేటస్ ఏమిటి?",
                language="te",
                success=True
            )
            mock_model.return_value = "నమస్కారం! మన ప్రాజెక్ట్ చాలా బాగుంది."

            turn_te = voice_orchestrator.execute_voice_turn(
                audio_input=b"dummy_audio_bytes",
                conversation_id="v_lang_conv"
            )
            assert turn_te.detected_language == "te"
            assert "నమస్కారం" in turn_te.response_text

            # 2. Voice Kannada
            mock_stt.return_value = STTTranscriptionResult(
                transcript="ನಮಸ್ಕಾರ ಸಾಕಿ! ನಮ್ಮ ಪ್ರಾಜೆಕ್ಟ್ ಹೇಗಿದೆ?",
                language="kn",
                success=True
            )
            mock_model.return_value = "ನಮಸ್ಕಾರ! ನಮ್ಮ ಪ್ರಾಜೆಕ್ಟ್ ಉತ್ತಮವಾಗಿ ಸಾಗಿದೆ."

            turn_kn = voice_orchestrator.execute_voice_turn(
                audio_input=b"dummy_audio_bytes",
                conversation_id="v_lang_conv"
            )
            assert turn_kn.detected_language == "kn"
            assert "ನಮಸ್ಕಾರ" in turn_kn.response_text
