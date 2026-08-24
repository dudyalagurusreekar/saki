"""
Saki Sprint 10 Reliability & Integration Test Suite: Real Audio-Reactive Saki Core
Verifies backend TTS WAV generation, Base64 payload delivery for browser Web Audio analysis,
audio lifecycle event tracking (SPEAKING -> IDLE/LISTENING), and barge-in coordination.
"""

import time
import io
import wave
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.tts_service import tts_service, AudioPlaybackManager
from backend.services.stt_service import stt_service
from backend.services.voice_orchestrator import voice_orchestrator
from backend.services.interruption_controller import interruption_controller
from backend.services.event_system import event_manager, SakiEvent, SakiEventType, SakiState


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestSprint10AudioReactive:
    """Complete automated test suite for Sprint 10 Real Audio-Reactive Saki Core."""

    def test_01_tts_synthesis_audio_payload_and_headers(self, client):
        """Verifies /api/voice/speak returns valid binary WAV stream with audio telemetry headers."""
        res = client.post("/api/voice/speak", json={
            "text": "Hello, I am Saki. Connecting your audio to my core.",
            "voice": "af_heart",
            "speed": 1.0,
            "conversation_id": "test-audio-01"
        })
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/wav"
        assert "X-TTS-Duration-Sec" in res.headers
        assert "X-TTS-Sample-Rate" in res.headers
        assert float(res.headers["X-TTS-Duration-Sec"]) > 0.5
        assert len(res.content) > 1000

        # Validate RIFF header
        with wave.open(io.BytesIO(res.content), "rb") as w:
            assert w.getnchannels() in [1, 2]
            assert w.getframerate() in [16000, 22050, 24000]
            assert w.getnframes() > 0

    def test_02_tts_synthesize_base64_json_payload(self, client):
        """Verifies /api/voice/synthesize returns Base64 data URI for Web Audio API decoding."""
        res = client.post("/api/voice/synthesize", json={
            "text": "Energy sphere expanding with vocal cadence.",
            "voice": "af_heart",
            "speed": 1.0,
            "conversation_id": "test-audio-02"
        })
        assert res.status_code == 200
        data = res.json()
        assert "audio_base64" in data
        assert data["audio_base64"].startswith("data:audio/wav;base64,")
        assert data["duration_seconds"] > 0.5
        assert data["sample_rate"] in [16000, 22050, 24000]

    def test_03_voice_turn_returns_audio_base64_for_reactor(self, client):
        """Verifies /api/voice/turn returns audio payload driving real-time core reactivity."""
        import base64
        synthetic_wav = tts_service.synthesize_response("What is the speed of light?", voice="af_heart")
        assert synthetic_wav is not None
        b64_str = base64.b64encode(synthetic_wav.audio_bytes).decode("utf-8")

        res = client.post("/api/voice/turn", json={
            "audio_base64": b64_str,
            "conversation_id": "test-audio-turn",
            "voice": "af_heart",
            "speed": 1.0,
            "play_locally": False
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["has_audio"] is True
        assert data["audio_base64"] is not None
        assert data["audio_base64"].startswith("data:audio/wav;base64,")
        assert data["audio_duration_sec"] > 0.5
        assert "speed of light" in data["transcript"].lower()

    def test_04_audio_waveform_sample_rate_and_channels(self):
        """Verifies low-level WAV structure is compatible with browser Web Audio AnalyserNode."""
        res = tts_service.synthesize_response("Testing Web Audio frequency decomposition.", voice="af_heart")
        assert res is not None
        assert len(res.audio_bytes) > 1000

        with wave.open(io.BytesIO(res.audio_bytes), "rb") as w:
            channels = w.getnchannels()
            sample_width = w.getsampwidth()
            framerate = w.getframerate()
            frames = w.getnframes()
            duration = frames / float(framerate)

            assert channels == 1 # Mono PCM
            assert sample_width == 2 # 16-bit PCM
            assert framerate == 24000
            assert duration > 0.5

    def test_05_amplitude_scaling_on_short_vs_long_utterance(self):
        """Verifies short utterance vs long sentence produce proportional audio lengths."""
        short_res = tts_service.synthesize_response("Hi.", voice="af_heart")
        long_res = tts_service.synthesize_response(
            "The quantum harmonic oscillator is the quantum-mechanical analog of the classical harmonic oscillator.",
            voice="af_heart"
        )
        assert short_res is not None and long_res is not None
        assert long_res.duration_seconds > short_res.duration_seconds * 2.0
        assert len(long_res.audio_bytes) > len(short_res.audio_bytes) * 2.0

    def test_06_speaking_state_event_emission_and_lifecycle(self):
        """Verifies SakiEventManager emits SPEAKING event during speech execution."""
        q = event_manager.subscribe_sync("test-audio-lifecycle")
        try:
            tts_service.synthesize_response("I am speaking with live audio telemetry.", conversation_id="test-audio-lifecycle")
            events_captured = []
            while not q.empty():
                events_captured.append(q.get_nowait())
            speaking_events = [e for e in events_captured if e.state == SakiState.SPEAKING]
            assert len(speaking_events) >= 1
            assert speaking_events[0].capability == "VOICE_SYNTHESIS"
        finally:
            event_manager.unsubscribe_sync(q, "test-audio-lifecycle")

    def test_07_immediate_barge_in_interruption_during_speaking(self, client):
        """Verifies barge-in stops active speech and transitions to LISTENING."""
        # 1. Start speech playback
        res_play = client.post("/api/voice/play", json={
            "text": "This is a long audio response being rendered on the core visual engine.",
            "voice": "af_heart",
            "conversation_id": "test-barge-in"
        })
        assert res_play.status_code == 200

        # 2. Trigger instant interruption
        t0 = time.perf_counter()
        res_intr = client.post("/api/voice/interrupt", json={
            "conversation_id": "test-barge-in",
            "reason": "user_voice_onset"
        })
        latency_ms = (time.perf_counter() - t0) * 1000.0

        assert res_intr.status_code == 200
        intr_data = res_intr.json()
        assert intr_data["status"] == "INTERRUPTED"
        assert latency_ms < 50.0 # Sub-50ms reaction target

    def test_08_audio_playback_stop_and_purge(self, client):
        """Verifies /api/voice/stop cancels active playback and flushes audio buffers."""
        res_stop = client.post("/api/voice/stop")
        assert res_stop.status_code == 200
        assert res_stop.json()["status"] == "stopped"

        assert tts_service.playback_manager.is_playing() is False


    def test_09_consecutive_audio_turns_without_desync(self, client):
        """Verifies multi-turn back-to-back audio generations maintain consistency."""
        for i in range(3):
            res = client.post("/api/voice/synthesize", json={
                "text": f"Turn number {i+1} audio reactivity test.",
                "voice": "af_heart",
                "conversation_id": "test-multi-turns"
            })
            assert res.status_code == 200
            assert res.json()["duration_seconds"] > 0.4

    def test_10_quiet_and_loud_voice_audio_properties(self):
        """Verifies punctuation and text formatting generate valid non-empty audio."""
        quiet_text = "whisper quiet contemplation..."
        loud_text = "WARNING! High energetic resonance detected!"

        q_res = tts_service.synthesize_response(quiet_text, voice="af_heart")
        l_res = tts_service.synthesize_response(loud_text, voice="af_heart")

        assert q_res is not None and len(q_res.audio_bytes) > 0
        assert l_res is not None and len(l_res.audio_bytes) > 0

    def test_11_fastapi_voice_endpoints_integrity(self, client):
        """Verifies all core voice routes return 200 OK and expected structure."""
        status_res = client.get("/api/voice/status")
        assert status_res.status_code == 200
        assert status_res.json()["kokoro_status"]["available"] is True

        voices_res = client.get("/api/voice/voices")
        assert voices_res.status_code == 200
        assert "af_heart" in voices_res.json()["voices"]

    def test_12_interruption_telemetry_and_config_persistence(self, client):
        """Verifies interruption config and status endpoints return valid metrics."""
        cfg_res = client.post("/api/voice/interruption/config", json={
            "min_speech_duration_ms": 120.0,
            "min_consecutive_chunks": 3,
            "vad_threshold": 0.5
        })
        assert cfg_res.status_code == 200
        assert cfg_res.json()["min_consecutive_chunks"] == 3

        stat_res = client.get("/api/voice/interruption/status")
        assert stat_res.status_code == 200
        data = stat_res.json()
        assert data["enabled"] is True
        assert "total_interruptions" in data

