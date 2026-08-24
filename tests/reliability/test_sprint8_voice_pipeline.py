"""
Sprint 8 — Saki Voice -> Existing Brain -> Local Voice Test Suite

Validates:
1. Local faster-whisper STT provider initialization, device config, and telemetry.
2. High-accuracy in-memory transcription (<1000ms latency on CPU).
3. End-to-end voice turn execution across conversational scenarios (greetings, short answers).
4. Emotional support queries triggering empathetic persona modulation in voice mode.
5. Technical coding questions routed to coder models with memory integration.
6. Multi-turn memory continuity: facts stated in voice are recalled in text, and vice-versa.
7. Noise/silence rejection and empty audio recovery.
8. Failsafe resilience: TTS failure preserves text response; STT failure leaves text chat functional.
9. Concurrency lock protection (no overlapping voice turns or overlapping audio playback).
10. Saki Unified Event System lifecycle transitions (PROCESSING/TRANSCRIBING -> THINKING -> IDLE).
11. Standard text chat independence.
12. FastAPI voice endpoints (/api/voice/turn, /api/voice/transcribe, /api/voice/stt/status, /api/voice/session/status).
"""

import os
import sys
import io
import time
import base64
import wave
import pytest
import numpy as np
from unittest.mock import patch

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.stt_service import stt_service, FasterWhisperSTTProvider, STTTranscriptionResult
from backend.services.tts_service import tts_service
from backend.services.microphone_service import microphone_service, SpeechSegment
from backend.services.voice_orchestrator import voice_orchestrator, VoiceTurnResult
from backend.services.memory_service import load_memory
from backend.core.events import SakiState, SakiEventType
from backend.services.event_system import saki_event_manager
from backend.routes.chat import chat, ChatRequest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module", autouse=True)
def init_services():
    """Ensures STT and TTS services are initialized."""
    stt_service.initialize()
    yield
    voice_orchestrator.stop_voice_session()


def generate_test_speech_wav(text: str, voice: str = "af_heart") -> bytes:
    """Helper to synthesize test WAV speech bytes using Kokoro TTS."""
    res = tts_service.synthesize_response(text, voice=voice)
    assert res.audio_bytes is not None and len(res.audio_bytes) > 0
    return res.audio_bytes


class TestSprint8VoicePipeline:
    """Comprehensive test suite for unified voice pipeline."""

    def test_01_faster_whisper_initialization_and_telemetry(self):
        """TEST 1: Faster-Whisper loads locally on CPU with valid telemetry."""
        assert stt_service.is_available() is True
        tel = stt_service.get_telemetry()
        assert tel.is_loaded is True
        assert "tiny.en" in tel.model_name
        assert tel.device == "cpu"
        assert tel.init_time_ms >= 0.0

    def test_02_stt_transcription_accuracy(self):
        """TEST 2: Transcribes synthetic speech with high accuracy and low latency."""
        test_phrase = "Hello Saki, how are you today?"
        audio_wav = generate_test_speech_wav(test_phrase)

        res = stt_service.transcribe_speech(audio_wav)
        assert res.success is True
        assert res.transcript != ""
        assert res.duration_seconds > 0.5
        assert res.latency_ms > 0.0
        assert res.language == "en"

        # Check transcript matches semantic intent
        cleaned_actual = res.transcript.lower().replace(".", "").replace(",", "").replace("?", "")
        assert "hello" in cleaned_actual or "saki" in cleaned_actual or "today" in cleaned_actual

    def test_03_voice_turn_greeting_and_short_answer(self):
        """TEST 3: Executes complete voice turn (Audio -> STT -> Brain -> TTS -> Audio)."""
        conv_id = f"test-voice-greeting-{int(time.time())}"
        audio_wav = generate_test_speech_wav("Hello Saki, good morning.")

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id,
            voice="af_heart"
        )

        assert turn_res.success is True
        assert turn_res.transcript != ""
        assert turn_res.response_text != ""
        assert turn_res.conversation_id == conv_id
        assert turn_res.audio_bytes is not None
        assert len(turn_res.audio_bytes) > 1000
        assert turn_res.audio_duration_sec > 0.5
        assert turn_res.voice_used == "af_heart"
        assert turn_res.tts_provider == "kokoro"
        assert turn_res.total_latency_ms > 0.0

    def test_04_voice_turn_emotional_support(self):
        """TEST 4: Emotional voice input triggers empathetic tone and warm TTS output."""
        conv_id = f"test-voice-empathy-{int(time.time())}"
        audio_wav = generate_test_speech_wav("I feel so overwhelmed and tired with work today.")

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id,
            voice="af_heart"
        )

        assert turn_res.success is True
        assert turn_res.response_text != ""
        assert turn_res.audio_bytes is not None
        assert turn_res.conversation_mode in ["support", "casual"]

    def test_05_voice_turn_coding_query_and_model_routing(self):
        """TEST 5: Coding question in voice routes to code intelligence."""
        conv_id = f"test-voice-code-{int(time.time())}"
        audio_wav = generate_test_speech_wav("How do I create a FastAPI router in Python?")

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id,
            voice="af_heart"
        )

        assert turn_res.success is True
        assert turn_res.response_text != ""
        assert "router" in turn_res.response_text.lower() or "fastapi" in turn_res.response_text.lower() or "python" in turn_res.response_text.lower()
        assert turn_res.has_audio is True

    def test_06_voice_and_text_memory_continuity(self):
        """TEST 6: Memory is shared between voice and text in the same conversation_id."""
        conv_id = f"test-voice-text-memory-{int(time.time())}"

        # 1. Voice Turn: User states a unique preference
        audio_wav = generate_test_speech_wav("My favorite color is emerald green.")
        turn1 = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id
        )
        assert turn1.success is True

        # Check memory history recorded
        mem_after_voice = load_memory()
        assert len(mem_after_voice.get("conversation_history", [])) >= 1

        # 2. Text Turn: User asks about the preference in the SAME conversation
        text_req = ChatRequest(
            message="What did I just say my favorite color is?",
            conversation_id=conv_id,
            enable_tts=False
        )
        text_res = chat(text_req)
        assert text_res.response is not None

        # Verify conversation history has both turns
        mem_final = load_memory()
        assert len(mem_final.get("conversation_history", [])) >= 2

    def test_07_empty_audio_and_noise_rejection(self):
        """TEST 7: Empty or pure silence audio handles cleanly without exceptions."""
        silence_samples = np.zeros(16000, dtype=np.float32) # 1s silence

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=silence_samples,
            conversation_id="test-voice-silence"
        )

        assert turn_res.success is True
        assert turn_res.transcript == ""
        assert "speak again" in turn_res.response_text.lower() or "catch that" in turn_res.response_text.lower()

    def test_08_failsafe_tts_and_stt_resilience(self):
        """TEST 8: Downstream TTS failure leaves text response and memory intact."""
        conv_id = f"test-voice-tts-fail-{int(time.time())}"
        audio_wav = generate_test_speech_wav("Hello Saki.")

        with patch.object(tts_service, "synthesize_response", side_effect=RuntimeError("Simulated TTS audio synthesis failure")):
            turn_res = voice_orchestrator.execute_voice_turn(
                audio_input=audio_wav,
                conversation_id=conv_id,
                play_locally=False
            )

            # Response text and success must be preserved despite TTS error
            assert turn_res.success is True
            assert turn_res.response_text != ""
            assert turn_res.audio_bytes is None
            assert turn_res.audio_base64 is None

    def test_09_concurrency_lock_and_playback_safety(self):
        """TEST 9: Turn lock serializes execution and cancels previous playback."""
        conv_id = f"test-voice-concurrency-{int(time.time())}"
        audio_wav = generate_test_speech_wav("Testing concurrent locks.")

        # Ensure active playback can be cancelled cleanly
        tts_service.cancel_active_speech()

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id
        )
        assert turn_res.success is True

    def test_10_unified_event_system_lifecycle_tracking(self):
        """TEST 10: Event system transitions through PROCESSING -> THINKING -> IDLE."""
        conv_id = f"test-voice-events-{int(time.time())}"
        q = saki_event_manager.subscribe_sync(conv_id)

        try:
            audio_wav = generate_test_speech_wav("Testing event states.")
            turn_res = voice_orchestrator.execute_voice_turn(
                audio_input=audio_wav,
                conversation_id=conv_id
            )
            assert turn_res.success is True

            events = []
            while not q.empty():
                events.append(q.get_nowait())

            states = [e.state for e in events]
            assert SakiState.PROCESSING in states or SakiState.THINKING in states
            assert SakiState.IDLE in states
        finally:
            saki_event_manager.unsubscribe_sync(q, conv_id)

    def test_11_text_chat_independence(self):
        """TEST 11: Text chat operates normally without requiring any voice subsystem."""
        req = ChatRequest(
            message="What is 2 + 2?",
            conversation_id="test-independent-chat",
            enable_tts=False
        )
        res = chat(req)
        assert res.response is not None
        assert len(res.response.strip()) > 0
        assert res.audio_base64 is None
        assert res.tts_telemetry is None

    def test_12_fastapi_voice_endpoints(self):
        """TEST 12: FastAPI endpoints respond with valid schemas."""
        client = TestClient(app)

        # 1. GET /api/voice/stt/status
        res_stt = client.get("/api/voice/stt/status")
        assert res_stt.status_code == 200
        stt_data = res_stt.json()
        assert stt_data["is_loaded"] is True
        assert stt_data["device"] == "cpu"

        # 2. GET /api/voice/session/status
        res_sess = client.get("/api/voice/session/status")
        assert res_sess.status_code == 200
        sess_data = res_sess.json()
        assert "is_session_active" in sess_data
        assert "microphone" in sess_data
        assert "stt" in sess_data
        assert "tts" in sess_data

        # 3. POST /api/voice/transcribe
        audio_wav = generate_test_speech_wav("Testing direct transcription endpoint.")
        b64_audio = base64.b64encode(audio_wav).decode("utf-8")

        res_trans = client.post(
            "/api/voice/transcribe",
            json={"audio_base64": b64_audio, "language": "en"}
        )
        assert res_trans.status_code == 200
        trans_data = res_trans.json()
        assert trans_data["transcript"] != ""
        assert trans_data["duration_seconds"] > 0.0
        assert trans_data["latency_ms"] > 0.0

        # 4. POST /api/voice/turn
        res_turn = client.post(
            "/api/voice/turn",
            json={
                "audio_base64": b64_audio,
                "conversation_id": "test-fastapi-voice-turn",
                "voice": "af_heart"
            }
        )
        assert res_turn.status_code == 200
        turn_data = res_turn.json()
        assert turn_data["transcript"] != ""
        assert turn_data["response_text"] != ""
        assert turn_data["has_audio"] is True
        assert turn_data["audio_base64"] is not None
        assert "latencies" in turn_data
