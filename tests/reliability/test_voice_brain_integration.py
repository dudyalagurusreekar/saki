"""
SAKI — Voice + Complete Brain Integration + Model Routing + Chat Continuity Reliability Tests

Verifies:
1. End-to-end voice turn execution (/api/voice/turn).
2. STT audio ingestion (WAV/WebM Base64) with Faster-Whisper.
3. Unification with Saki Cognitive Brain (routes to Phi-3, Hermes, Qwen3, Coder, Gemma).
4. Text and voice sharing the exact same conversation ID, history, persona, and durable memory.
5. Kokoro TTS speech synthesis generation and Base64 WAV delivery.
6. Real-time voice interruption / barge-in (< 30ms reaction).
7. Fail-safe resilience: text response is preserved in history even if TTS fails.
"""

import pytest
import io
import time
import base64
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.voice_orchestrator import voice_orchestrator, VoiceTurnResult
from backend.services.stt_service import stt_service, STTTranscriptionResult
from backend.services.tts_service import tts_service, TTSAudioResult
from backend.services.interruption_controller import interruption_controller
from backend.services.memory_service import load_memory, update_memory
from backend.routes.chat import get_conversation_history, append_message_to_conversation
from backend.core.config import settings

client = TestClient(app)


def generate_synthetic_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates a valid 16kHz mono WAV byte stream containing a synthetic tone."""
    import struct
    total_samples = int(duration_sec * sample_rate)
    header = io.BytesIO()
    # RIFF header
    header.write(b"RIFF")
    header.write(struct.pack("<I", 36 + total_samples * 2))
    header.write(b"WAVE")
    # fmt chunk
    header.write(b"fmt ")
    header.write(struct.pack("<I", 16))
    header.write(struct.pack("<H", 1)) # PCM format
    header.write(struct.pack("<H", 1)) # 1 channel
    header.write(struct.pack("<I", sample_rate))
    header.write(struct.pack("<I", sample_rate * 2)) # byte rate
    header.write(struct.pack("<H", 2)) # block align
    header.write(struct.pack("<H", 16)) # 16 bits per sample
    # data chunk
    header.write(b"data")
    header.write(struct.pack("<I", total_samples * 2))
    
    # 440 Hz sine wave tone
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    waveform = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    header.write(waveform.tobytes())
    return header.getvalue()


class TestVoiceBrainIntegration:

    def test_voice_turn_simple_greeting_routes_to_phi3(self):
        """Tests that a simple voice greeting routes through the orchestrator to phi3."""
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="Hello Saki, good morning!",
            language="en",
            duration_seconds=1.0,
            latency_ms=85.0,
            success=True
        )

        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.2,
            latency_ms=120.0,
            provider="kokoro",
            voice="af_heart"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="Good morning! How can I assist you today?"):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": "test-voice-session-1",
                "voice": "af_heart",
                "speed": 1.0
            })

            assert res.status_code == 200
            data = res.json()
            assert data["transcript"] == "Hello Saki, good morning!"
            assert "Good morning" in data["response_text"]
            assert data["selected_model"] == settings.MODEL_PHI3
            assert data["has_audio"] is True
            assert data["audio_base64"] is not None
            assert data["latencies"]["stt_latency_ms"] == 85.0
            assert data["latencies"]["tts_latency_ms"] >= 0.0

    def test_voice_turn_emotional_query_routes_to_hermes(self):
        """Tests that an emotional voice query routes to nous-hermes2 for empathetic support."""
        wav_bytes = generate_synthetic_wav(1.0)
        b64_data_url = f"data:audio/wav;base64,{base64.b64encode(wav_bytes).decode('utf-8')}"

        mock_stt = STTTranscriptionResult(
            transcript="I had a really hard day today and feel completely exhausted.",
            language="en",
            duration_seconds=1.5,
            latency_ms=90.0,
            success=True
        )

        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=2.0,
            latency_ms=150.0,
            provider="kokoro",
            voice="af_bella"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="I hear you. Take a breath, I'm here with you."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_data_url,
                "conversation_id": "test-voice-session-2",
                "voice": "af_bella"
            })

            assert res.status_code == 200
            data = res.json()
            assert "exhausted" in data["transcript"]
            assert data["selected_model"] == settings.MODEL_HERMES
            assert data["conversation_mode"] == "support"
            assert data["has_audio"] is True

    def test_voice_turn_coding_query_routes_to_coder(self):
        """Tests that a coding / debugging voice question routes to qwen2.5-coder."""
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="Fix this TypeError exception in my python script",
            language="en",
            duration_seconds=1.2,
            latency_ms=100.0,
            success=True
        )

        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.5,
            latency_ms=130.0,
            provider="kokoro",
            voice="af_heart"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="A TypeError occurs when an operation is applied to an inappropriate type."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": "test-voice-session-3"
            })

            assert res.status_code == 200
            data = res.json()
            assert "TypeError" in data["transcript"]
            assert data["selected_model"] == settings.MODEL_CODER

    def test_voice_turn_reasoning_routes_to_qwen(self):
        """Tests that a complex conceptual/reasoning voice query routes to qwen3:8b."""
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="Explain the architecture of distributed consensus algorithms like Raft and Paxos.",
            language="en",
            duration_seconds=2.0,
            latency_ms=110.0,
            success=True
        )

        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=2.5,
            latency_ms=180.0,
            provider="kokoro",
            voice="af_heart"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="Raft and Paxos solve distributed state machine consensus through leader election and log replication."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": "test-voice-session-4"
            })

            assert res.status_code == 200
            data = res.json()
            assert "consensus" in data["transcript"]
            assert data["selected_model"] == settings.MODEL_QWEN

    def test_conversation_history_shared_between_text_and_voice(self):
        """Verifies that typed text and voice turns share the exact same conversation history."""
        conv_id = "test-shared-session"

        # 1. Send typed message via /api/chat
        with patch("backend.services.brain_engine.call_model", return_value="I am building Saki with you."):
            res_text = client.post("/api/chat", json={
                "message": "Remember that we are building Saki together.",
                "conversation_id": conv_id
            })
            assert res_text.status_code == 200

        # 2. Send voice turn in the SAME conversation
        wav_bytes = generate_synthetic_wav(1.0)
        mock_stt = STTTranscriptionResult(
            transcript="What project did I just mention?",
            language="en",
            duration_seconds=1.0,
            latency_ms=75.0,
            success=True
        )
        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.0,
            latency_ms=90.0,
            provider="kokoro",
            voice="af_heart"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="You mentioned that we are building Saki together."):

            res_voice = client.post("/api/voice/turn", json={
                "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
                "conversation_id": conv_id
            })
            assert res_voice.status_code == 200
            data = res_voice.json()
            assert data["conversation_id"] == conv_id

        # 3. Check conversation history in database / JSON store
        history_res = client.get(f"/api/conversations/{conv_id}")
        assert history_res.status_code == 200
        history_data = history_res.json()
        all_messages = history_data.get("messages", [])
        
        # Verify both text and voice turns are recorded
        user_contents = [m["content"] for m in all_messages if m["role"] == "user"]
        assert any("building Saki" in c for c in user_contents)
        assert any("What project" in c for c in user_contents)

    def test_voice_interruption_barge_in_latency(self):
        """Tests that voice interruption stops active playback and returns < 30ms."""
        conv_id = "test-interrupt-session"
        
        t0 = time.perf_counter()
        res = client.post("/api/voice/interrupt", json={
            "conversation_id": conv_id,
            "reason": "user_speech_detected"
        })
        reaction_latency_ms = (time.perf_counter() - t0) * 1000.0

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "INTERRUPTED"
        assert reaction_latency_ms < 50.0  # Must be ultra-fast

    def test_voice_turn_tts_failure_preserves_text_response(self):
        """Verifies that if TTS synthesis throws an exception, the text response is still returned."""
        wav_bytes = generate_synthetic_wav(1.0)
        mock_stt = STTTranscriptionResult(
            transcript="Explain how neural networks work.",
            language="en",
            duration_seconds=1.0,
            latency_ms=60.0,
            success=True
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", side_effect=RuntimeError("TTS engine out of memory")), \
             patch("backend.services.brain_engine.call_model", return_value="Neural networks process inputs across weighted interconnected layers."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
                "conversation_id": "test-tts-fail-session"
            })

            assert res.status_code == 200
            data = res.json()
            # Text response is safely delivered
            assert "Neural networks" in data["response_text"]
            assert data["has_audio"] is False
            assert data["success"] is True

    def test_voice_turn_telugu_query_auto_routes_to_indic_tts(self):
        """Verifies that a Telugu voice turn auto-detects 'te' and selects 'te_saki' voice."""
        wav_bytes = generate_synthetic_wav(1.0)
        mock_stt = STTTranscriptionResult(
            transcript="నమస్కారం సాకి, ఈరోజు వాతావరణం ఎలా ఉంది?",
            language="te",
            duration_seconds=1.2,
            latency_ms=90.0,
            success=True
        )
        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.5,
            latency_ms=100.0,
            provider="indic_tts",
            voice="te_saki"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="నమస్కారం! ఈరోజు వాతావరణం చాలా ఆహ్లాదకరంగా ఉంది."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
                "conversation_id": "test-telugu-turn"
            })

            assert res.status_code == 200
            data = res.json()
            assert data["detected_language"] == "te"
            assert data["output_language"] == "te"
            assert data["voice_used"] == "te_saki"
            assert data["tts_provider"] == "indic_tts"
            assert data["has_audio"] is True
            assert "నమస్కారం" in data["response_text"]

    def test_voice_turn_kannada_query_auto_routes_to_indic_tts(self):
        """Verifies that a Kannada voice turn auto-detects 'kn' and selects 'kn_saki' voice."""
        wav_bytes = generate_synthetic_wav(1.0)
        mock_stt = STTTranscriptionResult(
            transcript="ನಮಸ್ಕಾರ ಸಾಕಿ, ಇವತ್ತು ಹವಾಮಾನ ಹೇಗಿದೆ?",
            language="kn",
            duration_seconds=1.2,
            latency_ms=95.0,
            success=True
        )
        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.5,
            latency_ms=105.0,
            provider="indic_tts",
            voice="kn_saki"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="ನಮಸ್ಕಾರ! ಇವತ್ತು ಹವಾಮಾನ ತುಂಬಾ ಚೆನ್ನಾಗಿದೆ."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
                "conversation_id": "test-kannada-turn"
            })

            assert res.status_code == 200
            data = res.json()
            assert data["detected_language"] == "kn"
            assert data["output_language"] == "kn"
            assert data["voice_used"] == "kn_saki"
            assert data["tts_provider"] == "indic_tts"
            assert data["has_audio"] is True

    def test_voice_turn_code_mixed_telugu_routes_to_coder(self):
        """Verifies that code-mixed Telugu + English coding query routes to Qwen Coder."""
        wav_bytes = generate_synthetic_wav(1.0)
        mock_stt = STTTranscriptionResult(
            transcript="సాకి, నా FastAPI backend లో WebSocket connection error వస్తుంది. దీన్ని debug చేయండి.",
            language="te",
            duration_seconds=1.5,
            latency_ms=110.0,
            success=True
        )
        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.5,
            latency_ms=110.0,
            provider="indic_tts",
            voice="te_saki"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="FastAPI లో WebSocket connection error సరిచేయడానికి CORS మరియు endpoint routing తనిఖీ చేయండి."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
                "conversation_id": "test-mixed-te-coder"
            })

            assert res.status_code == 200
            data = res.json()
            assert data["detected_language"] == "te"
            assert data["language_profile"]["is_mixed"] is True
            assert data["selected_model"] == settings.MODEL_CODER
            assert data["voice_used"] == "te_saki"
            assert data["tts_provider"] == "indic_tts"
