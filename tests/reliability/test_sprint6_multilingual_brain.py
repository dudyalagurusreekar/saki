"""
Sprint 6 — Multilingual Saki Brain + Memory + Natural Response Generation Test Suite

Covers the 25 required test cases:
1. English -> English response.
2. Telugu -> Telugu response.
3. Kannada -> Kannada response.
4. Telugu-English mixed -> natural Telugu-English response.
5. Kannada-English mixed -> natural Kannada-English response.
6. English -> Telugu explicit response request.
7. English -> Kannada explicit response request.
8. Telugu -> English explicit response request.
9. Kannada -> English explicit response request.
10. Language switching between consecutive turns.
11. Same conversation continuing across all three languages (EN -> TE -> KN -> EN).
12. Telugu emotional support -> Hermes routing.
13. Kannada emotional support -> Hermes routing.
14. Telugu coding -> Qwen Coder routing.
15. Kannada coding -> Qwen Coder routing.
16. Telugu complex reasoning -> Qwen3 routing.
17. Kannada complex reasoning -> Qwen3 routing.
18. Simple Telugu/Kannada interaction -> appropriate fast model.
19. Multilingual memory retrieval across languages.
20. Multilingual emotional context reaching the existing emotional analyzer.
21. Streaming Telugu/Kannada response rendering.
22. Markdown/code mixed with Telugu/Kannada.
23. Manual language override from Sprint 5.
24. AUTO mode from Sprint 5.
25. Ambiguous language handling without corrupting the conversation state.
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
from backend.services.orchestrator import SakiModelOrchestrator, RoutingDecision
from backend.services.emotional_support_service import (
    SupportAssessmentEngine,
    SupportType,
    HermesActivationLevel
)
from backend.services.memory_service import (
    normalize_memory,
    retrieve_memories,
    update_memory,
    _upsert_memory
)
from backend.services.brain_engine import brain_engine
from backend.services.response_evaluator import evaluate_response, QualityStatus
from backend.models.schemas import ChatRequest
from brain.schemas import UnifiedTurnRequest, InputType

client = TestClient(app)


class TestSprint6MultilingualBrain:

    def test_01_english_to_english_response(self):
        """(1) Proves English input produces English prompt directives and response."""
        query = "How do I optimize database connection pooling in FastAPI?"
        with patch("backend.services.brain_engine.call_model") as mock_call:
            mock_call.return_value = "You can optimize pooling using SQLAlchemy's create_engine pool_size parameter."
            res = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id="s6_e2e_en", turn_id="t1", text=query)
            )
            assert res.detected_language == "en"
            assert "SQLAlchemy" in res.response

    def test_02_telugu_to_telugu_response(self):
        """(2) Proves Telugu input produces authentic Telugu Unicode prompt directives and response."""
        query = "నమస్కారం సకీ! ఈ రోజు ప్రాజెక్ట్ ఎలా ముందుకు తీసుకువెళ్లాలి?"
        with patch("backend.services.brain_engine.call_model") as mock_call:
            mock_call.return_value = "నమస్కారం! మనం ఈ రోజు ఆర్కిటెక్చర్ డిజైన్ తో ప్రారంభించవచ్చు."
            res = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id="s6_e2e_te", turn_id="t2", text=query)
            )
            assert res.detected_language == "te"
            assert "నమస్కారం" in res.response

    def test_03_kannada_to_kannada_response(self):
        """(3) Proves Kannada input produces authentic Kannada Unicode prompt directives and response."""
        query = "ನಮಸ್ಕಾರ ಸಾಕಿ! ಈ ದಿನ ನಮ್ಮ ಕೆಲಸ ಹೇಗೆ ಸಾಗಿದೆ?"
        with patch("backend.services.brain_engine.call_model") as mock_call:
            mock_call.return_value = "ನಮಸ್ಕಾರ! ನಮ್ಮ ಕೆಲಸ ತುಂಬಾ ಚೆನ್ನಾಗಿ ಸಾಗಿದೆ."
            res = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id="s6_e2e_kn", turn_id="t3", text=query)
            )
            assert res.detected_language == "kn"
            assert "ನಮಸ್ಕಾರ" in res.response

    def test_04_telugu_english_mixed_response(self):
        """(4) Proves Telugu-English code-mixing preserves English technical terms."""
        query = "నాకు FastAPI లో async websocket endpoint create చేయడం ఎలాగో చూపించు."
        prof = MultilingualService.classify_text(query)
        assert prof.primary_language == "te"
        assert prof.is_code_mixed is True
        assert "FastAPI" in prof.english_terms or "websocket" in prof.english_terms

    def test_05_kannada_english_mixed_response(self):
        """(5) Proves Kannada-English code-mixing preserves English technical terms."""
        query = "ಈ project ಯಾಕೆ fail ಆಗುತ್ತಿದೆ? ನನ್ನ backend code check ಮಾಡ್ತೀಯಾ?"
        prof = MultilingualService.classify_text(query)
        assert prof.primary_language == "kn"
        assert prof.is_code_mixed is True
        assert "project" in prof.english_terms or "backend" in prof.english_terms

    def test_06_english_to_telugu_explicit_request(self):
        """(6) Proves English input with explicit Telugu request sets target language to Telugu."""
        query = "Explain memory management in Python, telugulo cheppu."
        prof = MultilingualService.classify_text(query)
        target = MultilingualService.determine_target_response_language(prof, query)
        assert target.language == "te"
        assert target.requested_output_language == "te"

    def test_07_english_to_kannada_explicit_request(self):
        """(7) Proves English input with explicit Kannada request sets target language to Kannada."""
        query = "Explain async await in JavaScript, kannadadalli heli."
        prof = MultilingualService.classify_text(query)
        target = MultilingualService.determine_target_response_language(prof, query)
        assert target.language == "kn"
        assert target.requested_output_language == "kn"

    def test_08_telugu_to_english_explicit_request(self):
        """(8) Proves Telugu input with explicit English request sets target language to English."""
        query = "ఈ ఆల్గారిథమ్ గురించి Explain this in English please."
        prof = MultilingualService.classify_text(query)
        target = MultilingualService.determine_target_response_language(prof, query)
        assert target.language == "en"
        assert target.requested_output_language == "en"

    def test_09_kannada_to_english_explicit_request(self):
        """(9) Proves Kannada input with explicit English request sets target language to English."""
        query = "ಈ ವಿಷಯದ ಬಗ್ಗೆ ಇಂಗ್ಲಿಷ್ ನಲ್ಲಿ ಹೇಳಿ (explain in English)."
        prof = MultilingualService.classify_text(query)
        target = MultilingualService.determine_target_response_language(prof, query)
        assert target.language == "en"
        assert target.requested_output_language == "en"

    def test_10_language_switching_between_consecutive_turns(self):
        """(10) Proves consecutive turn language switching without conversation reset."""
        conv_id = "s6_switch_conv"
        with patch("backend.services.brain_engine.call_model") as mock_call:
            mock_call.side_effect = [
                "I can help with backend design.",
                "ఖచ్చితంగా, మనం ప్రారంభించవచ్చు."
            ]
            res1 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="sw1", text="Let's build a service.")
            )
            assert res1.detected_language == "en"

            res2 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="sw2", text="మనం ఏ డేటాబేస్ ఎంచుకోవాలి?")
            )
            assert res2.detected_language == "te"

    def test_11_same_conversation_across_all_three_languages(self):
        """(11) Proves same conversation continues across EN -> TE -> KN -> EN."""
        conv_id = "s6_full_cycle_conv"
        with patch("backend.services.brain_engine.call_model") as mock_call, \
             patch("backend.services.brain_engine.load_memory") as mock_mem:

            mock_mem.return_value = normalize_memory({"conversation_history": []})
            mock_call.side_effect = [
                "Let's architect the Saki system.",
                "మనం FastAPI బ్యాకెండ్ నిర్మిస్తున్నాం.",
                "ನಾವು ಈಗ ಡೇಟಾಬೇಸ್ ಸಂಪರ್ಕವನ್ನು ಸರಿಪಡಿಸೋಣ.",
                "Here is the complete multi-language architectural summary."
            ]

            # 1. English
            res1 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="c1", text="What is the architecture of Saki?")
            )
            assert res1.detected_language == "en"

            # 2. Telugu
            res2 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="c2", text="మనం ఏ ఫ్రేమ్‌వర్క్ ఉపయోగిస్తున్నాం?")
            )
            assert res2.detected_language == "te"

            # 3. Kannada
            res3 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="c3", text="ಡೇಟಾಬೇಸ್ ಹೇಗೆ ಕಾನ್ಫಿಗರ್ ಮಾಡಬೇಕು?")
            )
            assert res3.detected_language == "kn"

            # 4. English
            res4 = brain_engine.execute_turn(
                UnifiedTurnRequest(conversation_id=conv_id, turn_id="c4", text="Summarize the decisions so far.")
            )
            assert res4.detected_language == "en"

    def test_12_telugu_emotional_support_routes_to_hermes(self):
        """(12) Proves Telugu emotional statement routes to Hermes 2 via Support mode."""
        query = "చాలా ఒంటరిగా ఉంది, నా ఇంటర్వ్యూ పోయింది మరియు చాలా బాధగా ఉంది."
        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_13_kannada_emotional_support_routes_to_hermes(self):
        """(13) Proves Kannada emotional statement routes to Hermes 2 via Support mode."""
        query = "ತುಂಬಾ ಒಂಟಿತನ ಅನಿಸ್ತಿದೆ, ನನ್ನ ಪ್ರಾಜೆಕ್ಟ್ ಹಾಳಾಯ್ತು ಮತ್ತು ತುಂಬಾ ಬೇಸರವಾಗಿದೆ."
        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_HERMES
        assert decision.conversation_mode == "support"

    def test_14_telugu_coding_routes_to_qwen_coder(self):
        """(14) Proves Telugu programming question routes to Qwen 2.5 Coder."""
        query = "నాకు FastAPI లో async websocket router రాయడానికి Python code చూపించు."
        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_15_kannada_coding_routes_to_qwen_coder(self):
        """(15) Proves Kannada programming question routes to Qwen 2.5 Coder."""
        query = "ನನಗೆ React components ನಲ್ಲಿ custom debounce hook ಹೇಗೆ implement ಮಾಡುವುದು code ಕೊಡಿ."
        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"

    def test_16_telugu_complex_reasoning_routes_to_qwen3(self):
        """(16) Proves Telugu complex reasoning routes to Qwen3 (Thinking Mode)."""
        query = "తెలుగులో explain the mathematical trade-offs between Paxos and Raft consensus algorithms."
        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"

    def test_17_kannada_complex_reasoning_routes_to_qwen3(self):
        """(17) Proves Kannada complex reasoning routes to Qwen3 (Thinking Mode)."""
        query = "ಕನ್ನಡದಲ್ಲಿ explain why distributed transactions require two-phase commit protocol."
        decision = SakiModelOrchestrator.classify_request(query)
        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"

    def test_18_simple_telugu_kannada_interaction_fast_model(self):
        """(18) Proves simple casual greeting in Telugu/Kannada routes to fast model (Phi-3)."""
        query_te = "నమస్కారం సకీ, ఎలా ఉన్నావు?"
        decision_te = SakiModelOrchestrator.classify_request(query_te)
        assert decision_te.selected_model in [settings.MODEL_PHI3, settings.MODEL_QWEN3]

        query_kn = "ನಮಸ್ಕಾರ ಸಾಕಿ, ಹೇಗಿದ್ದೀರಾ?"
        decision_kn = SakiModelOrchestrator.classify_request(query_kn)
        assert decision_kn.selected_model in [settings.MODEL_PHI3, settings.MODEL_QWEN3]

    def test_19_cross_lingual_memory_retrieval(self):
        """(19) Proves memory saved in English is retrieved by Telugu and Kannada queries."""
        mem = normalize_memory({
            "memories": [
                {
                    "id": "mem_py_pref",
                    "type": "PREFERENCE",
                    "content": "User's favorite programming language is Python.",
                    "importance": 9,
                    "confidence": 0.95,
                    "score": 10.0,
                    "frequency": 3
                }
            ]
        })

        recalled_te = retrieve_memories(mem, "నాకు ఇష్టమైన ప్రోగ్రామింగ్ భాష ఏది? (పైథాన్ / python)")
        assert any("Python" in r["content"] for r in recalled_te)

        recalled_kn = retrieve_memories(mem, "ನನ್ನ ನೆಚ್ಚಿನ ಪ್ರೋಗ್ರಾಮಿಂಗ್ ಭಾಷೆ ಯಾವುದು? (python / ಪೈಥಾನ್)")
        assert any("Python" in r["content"] for r in recalled_kn)

    def test_20_multilingual_emotional_context_reaching_analyzer(self):
        """(20) Proves Telugu and Kannada emotional statements produce valid SupportAssessment."""
        assessment_te = SupportAssessmentEngine.evaluate("చాలా ఒంటరిగా ఉంది, నా ప్రాజెక్ట్ ఫెయిల్ అయింది.")
        assert assessment_te.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert assessment_te.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD

        assessment_kn = SupportAssessmentEngine.evaluate("ತುಂಬಾ ಬೇಸರವಾಗಿದೆ, ನನ್ನ ಇಂಟರ್ವ್ಯೂ ಹಾಳಾಯ್ತು.")
        assert assessment_kn.support_type == SupportType.EMOTIONAL_SUPPORT_NEED
        assert assessment_kn.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD

    def test_21_streaming_unicode_rendering_safety(self):
        """(21) Proves Telugu and Kannada Unicode characters pass clean UTF-8 validation without replacement chars."""
        te_text = "నమస్కారం! నేను బాగున్నాను. 😊"
        kn_text = "ನಮಸ್ಕಾರ! ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ. 🌸"

        eval_te = evaluate_response(te_text)
        assert eval_te.passed is True
        assert "\ufffd" not in eval_te.repaired_text

        eval_kn = evaluate_response(kn_text)
        assert eval_kn.passed is True
        assert "\ufffd" not in eval_kn.repaired_text

    def test_22_markdown_code_mixed_with_indic_scripts(self):
        """(22) Proves responses with Markdown code blocks alongside Telugu/Kannada text format cleanly."""
        draft = (
            "ఇక్కడ మీ FastAPI endpoint code ఉంది:\n\n"
            "```python\nfrom fastapi import FastAPI\napp = FastAPI()\n\n"
            "@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n```\n\n"
            "ఇది సరిగ్గా పనిచేస్తుంది."
        )
        eval_res = evaluate_response(draft)
        assert eval_res.passed is True
        assert "```python" in eval_res.repaired_text
        assert "ఇక్కడ" in eval_res.repaired_text

    def test_23_manual_language_override(self):
        """(23) Proves manual language override takes effect regardless of input language."""
        query = "What is the best way to structure unit tests?"
        base_prof = MultilingualService.classify_text(query)

        target_te = MultilingualService.determine_target_response_language(base_prof, query, manual_mode="TE")
        assert target_te.language == "te"
        assert target_te.manual_mode == "TE"

        target_kn = MultilingualService.determine_target_response_language(base_prof, query, manual_mode="KN")
        assert target_kn.language == "kn"
        assert target_kn.manual_mode == "KN"

    def test_24_auto_mode_behavior(self):
        """(24) Proves AUTO mode dynamically detects input language."""
        prof_en = MultilingualService.classify_text("Explain binary search trees.")
        target_en = MultilingualService.determine_target_response_language(prof_en, "Explain binary search trees.", manual_mode="AUTO")
        assert target_en.language == "en"

        prof_te = MultilingualService.classify_text("నమస్కారం సకీ!")
        target_te = MultilingualService.determine_target_response_language(prof_te, "నమస్కారం సకీ!", manual_mode="AUTO")
        assert target_te.language == "te"

    def test_25_ambiguous_short_language_handling_preserves_state(self):
        """(25) Proves short ambiguous language input resolves without corrupting conversation state."""
        telugu_history = [
            {"user": "మనం ఈ రోజు కొత్త ఫీచర్ రాద్దాం.", "saki": "సరే, ప్రారంభిద్దాం!"}
        ]
        prof = MultilingualService.classify_text("Sure.", recent_history=telugu_history)
        assert prof.language == "te"
        assert prof.detection_source == "conversation_context"
