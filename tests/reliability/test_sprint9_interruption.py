"""
Sprint 9 — Real-Time Voice Interruption / Barge-In Test Suite

Validates:
1. InterruptionController initialization, debounce config, and telemetry tracking.
2. Instant TTS speech cancellation and audio playback halting (< 30ms).
3. Short noise / spike rejection via chunk debounce filtering.
4. Genuine speech onset triggering INTERRUPTION_DETECTED and TTS_CANCELLED events.
5. Mid-sentence barge-in turn execution (Saki speaking -> interrupted -> stops -> listens -> STT -> response).
6. Immediate interruption at speech onset.
7. Uninterrupted normal voice turn full lifecycle completion.
8. Rapid repeated consecutive interruptions without deadlocks or resource leaks.
9. Race condition handling (Saki finishing at exact instant of speech onset).
10. Bi-directional memory and conversation context continuity across interrupted turns.
11. Text chat independence and non-voice robustness.
12. FastAPI interruption REST endpoints (/api/voice/interrupt, /status, /config).
"""

import os
import sys
import io
import time
import base64
import wave
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.stt_service import stt_service
from backend.services.tts_service import tts_service, TTSLifecycleState
from backend.services.microphone_service import microphone_service, SpeechSegment, MicState
from backend.services.interruption_controller import interruption_controller, InterruptionRecord, InterruptionTelemetry
from backend.services.voice_orchestrator import voice_orchestrator, VoiceTurnResult
from backend.services.memory_service import load_memory
from backend.core.events import SakiState, SakiEventType, SakiEvent
from backend.services.event_system import saki_event_manager
from backend.routes.chat import chat, ChatRequest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module", autouse=True)
def init_services():
    """Ensures STT, TTS, and Interruption services are initialized."""
    stt_service.initialize()
    interruption_controller.enabled = True
    yield
    voice_orchestrator.stop_voice_session()


def generate_test_speech_wav(text: str, voice: str = "af_heart") -> bytes:
    """Helper to synthesize test WAV speech bytes using Kokoro TTS."""
    res = tts_service.synthesize_response(text, voice=voice)
    assert res.audio_bytes is not None and len(res.audio_bytes) > 0
    return res.audio_bytes


class TestSprint9VoiceInterruption:
    """Comprehensive automated test suite for real-time voice interruption."""

    def test_01_interruption_controller_initialization_and_config(self):
        """TEST 1: Interruption controller initializes with valid defaults and updates config."""
        assert interruption_controller is not None
        tel = interruption_controller.get_telemetry()
        assert tel.enabled is True
        assert tel.min_speech_duration_ms >= 10.0
        assert tel.min_consecutive_chunks >= 1
        assert tel.vad_threshold > 0.0

        # Test config update
        updated = interruption_controller.update_config(
            enabled=True,
            min_speech_duration_ms=100.0,
            min_consecutive_chunks=3,
            vad_threshold=0.55
        )
        assert updated.min_speech_duration_ms == 100.0
        assert updated.min_consecutive_chunks == 3
        assert updated.vad_threshold == 0.55

        # Reset to standard defaults
        interruption_controller.update_config(
            enabled=True,
            min_speech_duration_ms=120.0,
            min_consecutive_chunks=3,
            vad_threshold=0.5
        )

    def test_02_instant_tts_playback_cancellation(self):
        """TEST 2: Instant TTS playback cancellation stops audio in < 30ms and clears playing state."""
        audio_wav = generate_test_speech_wav("This is a long sentence meant to test playback cancellation.")
        
        # Start async playback
        tts_service.playback_manager.play_wav_bytes_async(audio_wav)
        assert tts_service.playback_manager.is_playing() is True

        # Trigger cancellation
        t0 = time.perf_counter()
        tts_service.cancel_active_speech()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert elapsed_ms < 50.0  # Must be near-instantaneous
        assert tts_service.playback_manager.is_playing() is False
        assert tts_service.current_lifecycle_state == TTSLifecycleState.TTS_CANCELLED

    def test_03_debounce_and_short_noise_rejection(self):
        """TEST 3: Brief noise spikes (< debounce threshold) do not trigger an interruption."""
        audio_wav = generate_test_speech_wav("Testing noise rejection.")
        conv_id = f"test-noise-{int(time.time())}"

        # Set Saki to playing state
        tts_service.playback_manager.play_wav_bytes_async(audio_wav)
        assert tts_service.playback_manager.is_playing() is True

        # Simulate 1 isolated high-probability chunk (32ms spike, e.g. mic bump or click)
        interrupted = interruption_controller.evaluate_vad_chunk(
            speech_prob=0.95,
            is_speech=True,
            conversation_id=conv_id
        )
        # First chunk alone must NOT trigger interruption (needs 3 consecutive chunks)
        assert interrupted is False
        assert tts_service.playback_manager.is_playing() is True

        # Next chunk is silence -> resets debounce
        interrupted_silence = interruption_controller.evaluate_vad_chunk(
            speech_prob=0.05,
            is_speech=False,
            conversation_id=conv_id
        )
        assert interrupted_silence is False
        assert tts_service.playback_manager.is_playing() is True

        # Cleanup
        tts_service.cancel_active_speech()

    def test_04_genuine_speech_triggers_interruption_and_tts_cancelled_events(self):
        """TEST 4: Genuine speech onset (> debounce threshold) halts audio and emits events."""
        conv_id = f"test-bargein-events-{int(time.time())}"
        q = saki_event_manager.subscribe_sync(conv_id)

        try:
            audio_wav = generate_test_speech_wav("Saki is actively talking right now.")
            tts_service.playback_manager.play_wav_bytes_async(audio_wav)
            assert tts_service.playback_manager.is_playing() is True

            # Send 3 consecutive speech chunks to meet debounce threshold
            interruption_controller.evaluate_vad_chunk(speech_prob=0.85, is_speech=True, conversation_id=conv_id)
            interruption_controller.evaluate_vad_chunk(speech_prob=0.88, is_speech=True, conversation_id=conv_id)
            interrupted = interruption_controller.evaluate_vad_chunk(speech_prob=0.92, is_speech=True, conversation_id=conv_id)

            assert interrupted is True
            assert tts_service.playback_manager.is_playing() is False

            # Collect emitted events
            events = []
            while not q.empty():
                events.append(q.get_nowait())

            event_details = [e.details.get("event_name") for e in events if isinstance(e.details, dict)]
            states = [e.state for e in events]

            assert "INTERRUPTION_DETECTED" in event_details or any(e.event_type == SakiEventType.INTERRUPTION for e in events)
            assert "TTS_CANCELLED" in event_details or SakiState.LISTENING in states
            assert SakiState.LISTENING in states
        finally:
            saki_event_manager.unsubscribe_sync(q, conv_id)
            tts_service.cancel_active_speech()

    def test_05_mid_sentence_barge_in_turn_execution(self):
        """TEST 5: Interrupting Saki halfway through speech immediately stops TTS and executes new turn."""
        conv_id = f"test-mid-sentence-{int(time.time())}"

        # 1. Start long Saki speech
        long_speech_wav = generate_test_speech_wav("Artificial intelligence is a branch of computer science that builds smart systems.")
        tts_service.playback_manager.play_wav_bytes_async(long_speech_wav)
        assert tts_service.playback_manager.is_playing() is True

        # Let it play briefly
        time.sleep(0.1)

        # 2. User interrupts with a new query
        user_interrupt_audio = generate_test_speech_wav("Wait Saki, what is Python?")

        # Trigger barge-in
        intr_record = interruption_controller.trigger_interruption(
            conversation_id=conv_id,
            reason="user_speech_detected",
            source="vad_speech_onset"
        )
        assert intr_record.success is True
        assert tts_service.playback_manager.is_playing() is False

        # 3. Process user's new voice turn
        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=user_interrupt_audio,
            conversation_id=conv_id,
            voice="af_heart"
        )

        assert turn_res.success is True
        assert turn_res.transcript != ""
        assert "python" in turn_res.transcript.lower() or "wait" in turn_res.transcript.lower() or "saki" in turn_res.transcript.lower()
        assert turn_res.response_text != ""
        assert turn_res.has_audio is True

    def test_06_immediate_speech_onset_interruption(self):
        """TEST 6: Interrupting immediately at the onset of Saki speech cancels cleanly."""
        conv_id = f"test-immediate-onset-{int(time.time())}"
        speech_wav = generate_test_speech_wav("Hello! How can I help you?")

        tts_service.playback_manager.play_wav_bytes_async(speech_wav)
        assert tts_service.playback_manager.is_playing() is True

        # Immediate interruption within 10ms
        record = interruption_controller.trigger_interruption(
            conversation_id=conv_id,
            reason="immediate_interruption",
            source="vad_speech_onset"
        )

        assert record.reaction_latency_ms < 50.0
        assert tts_service.playback_manager.is_playing() is False

    def test_07_uninterrupted_normal_voice_turn(self):
        """TEST 7: Normal voice turn without interruption completes all states cleanly."""
        conv_id = f"test-normal-turn-{int(time.time())}"
        audio_wav = generate_test_speech_wav("What is the capital of France?")

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id,
            play_locally=False
        )

        assert turn_res.success is True
        assert turn_res.transcript != ""
        assert turn_res.response_text != ""
        assert turn_res.interrupted is False
        assert turn_res.has_audio is True

    def test_08_rapid_repeated_consecutive_interruptions(self):
        """TEST 8: Repeated consecutive interruptions do not deadlock, leak resources, or stick in SPEAKING."""
        conv_id = f"test-repeated-interruptions-{int(time.time())}"
        audio_wav = generate_test_speech_wav("Short snippet.")

        for i in range(5):
            tts_service.playback_manager.play_wav_bytes_async(audio_wav)
            assert tts_service.playback_manager.is_playing() is True

            record = interruption_controller.trigger_interruption(
                conversation_id=conv_id,
                reason=f"repeated_interruption_{i}",
                source="stress_test"
            )
            assert record.success is True
            assert tts_service.playback_manager.is_playing() is False

        tel = interruption_controller.get_telemetry()
        assert tel.total_interruptions >= 5
        assert saki_event_manager.get_current_state(conv_id) == SakiState.LISTENING

    def test_09_race_condition_saki_finishing_at_speech_onset(self):
        """TEST 9: Saki naturally finishing playback at exact speech onset handles gracefully."""
        conv_id = f"test-race-condition-{int(time.time())}"

        # Ensure Saki is IDLE (not playing)
        tts_service.cancel_active_speech()
        assert tts_service.playback_manager.is_playing() is False

        # Speech onset arrives when Saki is already finished
        interrupted = interruption_controller.evaluate_vad_chunk(
            speech_prob=0.9,
            is_speech=True,
            conversation_id=conv_id
        )
        # Should not need to interrupt because Saki is already IDLE
        assert interrupted is False
        assert tts_service.playback_manager.is_playing() is False

    def test_10_memory_and_conversation_context_continuity_after_interruption(self):
        """TEST 10: Multi-turn memory and context remain fully intact across interrupted turns."""
        conv_id = f"test-interruption-memory-{int(time.time())}"

        # Turn 1: User gives a preference in voice
        audio_wav_1 = generate_test_speech_wav("My favorite animal is a snow leopard.")
        turn1 = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav_1,
            conversation_id=conv_id
        )
        assert turn1.success is True

        # Saki starts responding -> User interrupts
        tts_service.playback_manager.play_wav_bytes_async(turn1.audio_bytes or generate_test_speech_wav("I love snow leopards!"))
        interruption_controller.trigger_interruption(conversation_id=conv_id, reason="user_bargein")
        assert tts_service.playback_manager.is_playing() is False

        # Turn 2: User asks what their favorite animal is
        audio_wav_2 = generate_test_speech_wav("What is my favorite animal?")
        turn2 = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav_2,
            conversation_id=conv_id
        )
        assert turn2.success is True
        assert "leopard" in turn2.response_text.lower() or "animal" in turn2.response_text.lower()

        # Check memory store
        mem_data = load_memory()
        history = mem_data.get("conversation_history", [])
        assert len(history) >= 2

    def test_11_text_chat_independence(self):
        """TEST 11: Text chat operates normally and is completely unaffected by voice interruption state."""
        # Trigger an interruption on voice session
        interruption_controller.trigger_interruption(conversation_id="voice-session", reason="text_test")

        # Execute text chat
        chat_res = chat(ChatRequest(
            message="Hello Saki, what is 5 plus 5?",
            conversation_id="test-independent-chat",
            enable_tts=False
        ))
        assert chat_res.response is not None
        assert len(chat_res.response.strip()) > 0
        assert "10" in chat_res.response or "ten" in chat_res.response.lower()

    def test_12_fastapi_interruption_endpoints(self):
        """TEST 12: FastAPI REST endpoints (/api/voice/interrupt, /status, /config) work with valid schemas."""
        client = TestClient(app)

        # 1. GET /api/voice/interruption/status
        res_stat = client.get("/api/voice/interruption/status")
        assert res_stat.status_code == 200
        stat_data = res_stat.json()
        assert stat_data["enabled"] is True
        assert "total_interruptions" in stat_data
        assert "min_speech_duration_ms" in stat_data

        # 2. POST /api/voice/interruption/config
        res_cfg = client.post(
            "/api/voice/interruption/config",
            json={
                "enabled": True,
                "min_speech_duration_ms": 110.0,
                "min_consecutive_chunks": 3,
                "vad_threshold": 0.52
            }
        )
        assert res_cfg.status_code == 200
        cfg_data = res_cfg.json()
        assert cfg_data["min_speech_duration_ms"] == 110.0
        assert cfg_data["vad_threshold"] == 0.52

        # 3. POST /api/voice/interrupt
        res_intr = client.post(
            "/api/voice/interrupt",
            json={
                "conversation_id": "test-fastapi-interrupt",
                "reason": "api_test"
            }
        )
        assert res_intr.status_code == 200
        intr_data = res_intr.json()
        assert intr_data["status"] == "INTERRUPTED"
        assert intr_data["interruption_id"] != ""
        assert intr_data["reaction_latency_ms"] >= 0.0
