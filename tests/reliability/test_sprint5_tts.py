import os
import sys
import io
import wave
import time
import threading
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.tts_service import (
    tts_service,
    normalize_text_for_speech,
    KokoroTTSProvider,
    PiperTTSProvider,
    TTSLifecycleState,
    TTSAudioResult
)
from backend.core.events import SakiState, SakiEventType
from backend.services.event_system import event_manager
from backend.routes.chat import ChatRequest, chat


class TestSprint5TTSService:
    """Comprehensive test suite for Sprint 5 TTS capability."""

    def test_01_text_normalization(self):
        """Verifies text normalization strips code blocks, markdown, emojis, and formats symbols."""
        raw_text = (
            "# Heading\n"
            "Hello **world**! Check [FastAPI](https://fastapi.tiangolo.com) & `uvicorn` server.\n"
            "```python\nprint('code block')\n```\n"
            "- Bullet point 1\n"
            "> A blockquote\n"
            "50% speed / 100% accuracy = success! 🌸✨"
        )
        cleaned = normalize_text_for_speech(raw_text)

        assert "print('code block')" not in cleaned, "Code block was not stripped"
        assert "```" not in cleaned, "Backticks were not stripped"
        assert "#" not in cleaned, "Markdown header was not stripped"
        assert "**" not in cleaned, "Bold marker was not stripped"
        assert "https://" not in cleaned, "URL was not stripped"
        assert "FastAPI" in cleaned, "Link anchor text was preserved"
        assert " and " in cleaned, "& was not converted to 'and'"
        assert " percent " in cleaned, "% was not converted to 'percent'"
        assert " or " in cleaned, "/ was not converted to 'or'"
        assert "🌸" not in cleaned, "Emoji was not removed"
        assert "✨" not in cleaned, "Emoji was not removed"

    def test_02_kokoro_initialization_and_status(self):
        """Verifies Kokoro engine initializes cleanly and reports accurate status metadata."""
        prov = tts_service.kokoro
        initialized = prov.initialize()
        assert initialized is True, f"Kokoro failed to initialize: {prov.get_status().get('error')}"

        status = prov.get_status()
        assert status["provider"] == "kokoro"
        assert status["initialized"] is True
        assert status["available"] is True
        assert status["sample_rate"] == 24000
        assert status["license"] == "Apache-2.0"
        assert "af_heart" in status["supported_female_voices"]
        assert status["recommended_voice"] == "af_heart"
        assert status["model_size_mb"] > 100
        assert status["voices_size_mb"] > 10

    def test_03_af_heart_synthesis_and_telemetry(self):
        """Verifies af_heart synthesizes valid 24kHz WAV audio with empirical telemetry."""
        prompt = "Hello! Saki local speech output is running."
        res = tts_service.synthesize_response(prompt, voice="af_heart", speed=1.0)

        assert isinstance(res, TTSAudioResult)
        assert len(res.audio_bytes) > 1000, "Audio bytes payload is too small"
        assert res.audio_bytes[:4] == b"RIFF", "Audio payload is not a valid RIFF WAV"
        assert res.sample_rate == 24000
        assert res.provider == "kokoro"
        assert res.voice == "af_heart"
        assert res.duration_seconds > 1.0, f"Expected duration > 1.0s, got {res.duration_seconds}"
        assert res.latency_ms > 0, "Latency must be a positive measurement"
        assert res.first_chunk_latency_ms > 0, "First chunk latency must be positive"
        assert res.rtf > 0, "Real-time factor must be positive"
        assert res.character_count == len(normalize_text_for_speech(prompt))
        assert res.memory_mb > 0, "Process memory measurement should be positive"

        # Verify WAV header integrity using wave module
        with wave.open(io.BytesIO(res.audio_bytes), "rb") as w:
            assert w.getnchannels() == 1, "Audio should be mono"
            assert w.getsampwidth() == 2, "Audio should be 16-bit PCM"
            assert w.getframerate() == 24000, "Audio should be 24000 Hz"

    def test_04_female_voices_coverage(self):
        """Verifies that all 5 target English female voices can synthesize speech."""
        female_voices = ["af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky"]
        test_phrase = "Testing voice tone."

        for voice in female_voices:
            res = tts_service.synthesize_response(test_phrase, voice=voice)
            assert res.voice == voice
            assert res.duration_seconds > 0.5
            assert len(res.audio_bytes) > 500

    def test_05_cancellation_token_handling(self):
        """Verifies cancellation token interrupts generation safely."""
        cancel_token = threading.Event()
        cancel_token.set()  # Pre-cancelled

        with pytest.raises(RuntimeError, match="cancelled"):
            tts_service.kokoro.synthesize(
                "This should not complete.",
                voice="af_heart",
                cancel_token=cancel_token
            )

    def test_06_event_system_lifecycle_tracking(self):
        """Verifies state transitions are emitted through SakiEventManager during synthesis."""
        conv_id = "test-tts-session"
        req_id = f"test_req_{int(time.time())}"

        # Listen for events
        q = event_manager.subscribe_sync(conv_id)
        try:
            res = tts_service.synthesize_response(
                "Short event test.",
                conversation_id=conv_id,
                request_id=req_id
            )
            assert res is not None

            # Collect events emitted
            events = []
            while not q.empty():
                events.append(q.get_nowait())

            states = [e.state for e in events]
            assert SakiState.SPEAKING in states, "SPEAKING state was not emitted"
            assert SakiState.IDLE in states, "IDLE state was not restored"
        finally:
            event_manager.unsubscribe_sync(q, conv_id)

    def test_07_piper_fallback_provider_interface(self):
        """Verifies Piper provider interface and fallback readiness."""
        piper = tts_service.piper
        status = piper.get_status()
        assert status["provider"] == "piper"
        assert status["sample_rate"] == 22050
        assert "en_US-amy-medium" in piper.get_voices()

    def test_08_chat_pipeline_tts_integration(self):
        """Verifies chat endpoint integrates TTS speech synthesis when enable_tts is requested."""
        # 1. TTS enabled request
        req_tts = ChatRequest(
            message="Hello Saki!",
            conversation_id="test-chat-tts",
            enable_tts=True,
            voice="af_heart"
        )
        res_tts = chat(req_tts)
        assert res_tts.response is not None
        assert res_tts.tts_telemetry is not None
        assert res_tts.tts_telemetry["provider"] == "kokoro"
        assert res_tts.tts_telemetry["voice"] == "af_heart"
        assert res_tts.audio_base64 is not None
        assert res_tts.audio_base64.startswith("data:audio/wav;base64,")

        # 2. TTS disabled request (zero overhead)
        req_no_tts = ChatRequest(
            message="Hello Saki without audio!",
            conversation_id="test-chat-no-tts",
            enable_tts=False
        )
        res_no_tts = chat(req_no_tts)
        assert res_no_tts.response is not None
        assert res_no_tts.tts_telemetry is None
        assert res_no_tts.audio_base64 is None

    def test_09_fail_safe_tts_resilience(self):
        """Verifies that a downstream TTS failure never breaks the LLM text response."""
        req = ChatRequest(
            message="Test resilience against TTS errors.",
            conversation_id="test-tts-resilience",
            enable_tts=True
        )

        with patch.object(tts_service, "synthesize_response", side_effect=RuntimeError("Simulated TTS audio failure")):
            res = chat(req)
            # Text response must succeed gracefully despite TTS failure
            assert res.response is not None
            assert len(res.response.strip()) > 5
            assert res.audio_base64 is None
            assert res.tts_telemetry is None
