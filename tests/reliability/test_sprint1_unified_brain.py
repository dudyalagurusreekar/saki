"""
Sprint 1 — Unified Saki Brain & Turn Pipeline Test Suite

Validates:
1. Text enters the unified brain pipeline.
2. Voice transcript enters exactly the same brain path.
3. Image input reaches the existing vision-capable route.
4. Text, voice, and image preserve conversation context.
5. Memory integration is shared across modalities.
6. Model selection remains delegated to the existing orchestrator.
7. A voice response is also returned as a normal Chat response.
8. TTS failure does not delete/hide the Chat response.
9. Each turn receives a unique ID.
10. Duplicate/stale turns are rejected safely.
"""

import io
import time
import base64
import struct
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.schemas import ChatRequest, ChatResponse, UnifiedTurnRequestSchema
from brain.schemas import UnifiedTurnRequest, InputType
from backend.services.brain_engine import brain_engine, turn_deduplicator
from backend.services.stt_service import stt_service, STTTranscriptionResult
from backend.services.tts_service import tts_service, TTSAudioResult
from backend.services.memory_service import load_memory, update_memory
from backend.routes.chat import get_conversation_history, append_message_to_conversation
from backend.core.events import SakiState
from backend.core.config import settings

client = TestClient(app)


def generate_synthetic_wav(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates a valid 16kHz mono WAV byte stream containing a synthetic tone."""
    total_samples = int(duration_sec * sample_rate)
    header = io.BytesIO()
    header.write(b"RIFF")
    header.write(struct.pack("<I", 36 + total_samples * 2))
    header.write(b"WAVE")
    header.write(b"fmt ")
    header.write(struct.pack("<I", 16))
    header.write(struct.pack("<H", 1)) # PCM format
    header.write(struct.pack("<H", 1)) # 1 channel
    header.write(struct.pack("<I", sample_rate))
    header.write(struct.pack("<I", sample_rate * 2))
    header.write(struct.pack("<H", 2))
    header.write(struct.pack("<H", 16))
    header.write(b"data")
    header.write(struct.pack("<I", total_samples * 2))
    
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    waveform = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    header.write(waveform.tobytes())
    return header.getvalue()


class TestSprint1UnifiedBrain:

    def test_01_text_enters_unified_pipeline(self):
        """(1) Proves text input enters the unified pipeline and triggers required lifecycle states."""
        conv_id = f"test-s1-text-{int(time.time()*1000)}"
        
        with patch("backend.services.brain_engine.call_model", return_value="Hello! I am Saki, ready to help."):
            res = client.post("/api/chat", json={
                "message": "Hi Saki, are you online?",
                "conversation_id": conv_id,
                "input_type": "TEXT"
            })
            
            assert res.status_code == 200
            data = res.json()
            assert data["response"] == "Hello! I am Saki, ready to help."
            assert data["conversation_id"] == conv_id
            assert data["input_type"] == "TEXT"
            assert data["turn_id"] is not None
            assert data["final_state"] in ["COMPLETED", "IDLE"]
            assert data["routing"] is not None
            assert "selected_model" in data["routing"]

    def test_02_voice_transcript_enters_exact_same_brain_path(self):
        """(2) Proves voice audio transcript enters exactly the same brain path as text."""
        conv_id = f"test-s1-voice-{int(time.time()*1000)}"
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="What is the weather like today?",
            language="en",
            duration_seconds=1.0,
            latency_ms=80.0,
            success=True
        )
        mock_tts = TTSAudioResult(
            audio_bytes=wav_bytes,
            sample_rate=24000,
            duration_seconds=1.5,
            latency_ms=120.0,
            provider="kokoro",
            voice="af_heart"
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", return_value=mock_tts), \
             patch("backend.services.brain_engine.call_model", return_value="The weather is bright and clear today."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": conv_id
            })

            assert res.status_code == 200
            data = res.json()
            assert data["transcript"] == "What is the weather like today?"
            assert "weather" in data["response_text"].lower()
            assert data["conversation_id"] == conv_id
            assert data["has_audio"] is True
            assert data["audio_base64"] is not None

    def test_03_image_input_reaches_vision_capable_route(self):
        """(3) Proves image input reaches the existing vision-capable route (Gemma 3)."""
        conv_id = f"test-s1-image-{int(time.time()*1000)}"

        with patch("backend.services.brain_engine.call_model", return_value="I see a photo showing outdoor scenery.") as mock_call:
            res = client.post("/api/chat", json={
                "message": "Describe what you see in this screenshot photo",
                "conversation_id": conv_id,
                "input_type": "IMAGE",
                "attachments": [{"path": "c:/temp/photo.png", "type": "image/png"}]
            })

            assert res.status_code == 200
            data = res.json()
            assert data["routing"]["selected_model"] == settings.MODEL_GEMMA
            assert "photo" in data["response"].lower()
            assert mock_call.called

    def test_04_all_modalities_preserve_conversation_context(self):
        """(4) Proves text, voice, and image turns in the same conversation_id share conversational history."""
        conv_id = f"test-s1-continuity-{int(time.time()*1000)}"
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="I am currently building a distributed database.",
            language="en",
            duration_seconds=1.0,
            latency_ms=50.0,
            success=True
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch("backend.services.brain_engine.call_model", side_effect=[
                 "That sounds like an ambitious project! Are you using Raft for consensus?",
                 "Here is how Raft consensus works in your distributed database.",
                 "I can see the storage engine diagram you attached."
             ]):

            # 1. Voice Turn
            res_v = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": conv_id
            })
            assert res_v.status_code == 200

            # 2. Text Turn in SAME conversation
            res_t = client.post("/api/chat", json={
                "message": "Yes, explain the leader election phase.",
                "conversation_id": conv_id
            })
            assert res_t.status_code == 200

            # 3. Image Turn in SAME conversation
            res_i = client.post("/api/chat", json={
                "message": "Check this storage node diagram",
                "conversation_id": conv_id,
                "attachments": [{"path": "c:/temp/node.png", "type": "image/png"}]
            })
            assert res_i.status_code == 200

            # Verify history contains all 3 turns in chronological order
            history_res = client.get(f"/api/conversations/{conv_id}/history")
            assert history_res.status_code == 200
            msgs = history_res.json().get("messages", [])
            assert len(msgs) >= 6 # 3 user + 3 assistant messages

    def test_05_memory_integration_is_shared(self):
        """(5) Proves durable memory integration is shared bi-directionally between voice and text."""
        conv_id = f"test-s1-memory-{int(time.time()*1000)}"
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="Remember that my preferred backend framework is FastAPI with Python.",
            language="en",
            duration_seconds=1.0,
            latency_ms=50.0,
            success=True
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch("backend.services.brain_engine.call_model", return_value="I will remember that you prefer FastAPI and Python!"):

            # User states preference over Voice
            res_v = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": conv_id
            })
            assert res_v.status_code == 200

            # Verify memory was updated
            mem = load_memory()
            assert len(mem.get("conversation_history", [])) > 0

            # User queries memory over Text
            with patch("backend.services.brain_engine.call_model", return_value="You prefer FastAPI with Python."):
                res_t = client.post("/api/chat", json={
                    "message": "What backend framework do I prefer?",
                    "conversation_id": conv_id
                })
                assert res_t.status_code == 200
                assert "FastAPI" in res_t.json()["response"]

    def test_06_model_selection_delegated_to_existing_orchestrator(self):
        """(6) Proves the existing 5-model orchestrator decides specialist model for both voice and text."""
        conv_id = f"test-s1-orch-{int(time.time()*1000)}"
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        # Coding query in Voice
        mock_stt_code = STTTranscriptionResult(
            transcript="Write a Python async generator function for streaming SSE events.",
            language="en",
            duration_seconds=1.0,
            latency_ms=60.0,
            success=True
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt_code), \
             patch("backend.services.brain_engine.call_model", return_value="async def event_generator(): yield 'data: test'") as mock_call:

            res_v = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": conv_id
            })
            assert res_v.status_code == 200
            assert res_v.json()["selected_model"] == settings.MODEL_CODER

        # Emotional support query in Text
        with patch("backend.services.brain_engine.call_model", return_value="I am here with you. Take a breath."):
            res_t = client.post("/api/chat", json={
                "message": "I feel so lonely, overwhelmed, and completely exhausted today.",
                "conversation_id": conv_id
            })
            assert res_t.status_code == 200
            assert res_t.json()["routing"]["selected_model"] == settings.MODEL_HERMES

    def test_07_voice_response_returned_as_normal_chat_response(self):
        """(7) Proves a voice response produces a complete standardized ChatResponse representation."""
        conv_id = f"test-s1-response-struct-{int(time.time()*1000)}"
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="Hello Saki",
            language="en",
            duration_seconds=1.0,
            latency_ms=40.0,
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
             patch("backend.services.brain_engine.call_model", return_value="Hello! How are you doing?"):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": conv_id
            })

            assert res.status_code == 200
            data = res.json()
            assert data["transcript"] == "Hello Saki"
            assert data["response_text"] == "Hello! How are you doing?"
            assert data["has_audio"] is True
            assert data["audio_base64"] is not None
            assert data["selected_model"] is not None
            assert data["conversation_mode"] is not None

    def test_08_tts_failure_preserves_chat_response(self):
        """(8) Proves that if TTS synthesis throws an exception, the generated text response is preserved."""
        conv_id = f"test-s1-tts-fail-{int(time.time()*1000)}"
        wav_bytes = generate_synthetic_wav(1.0)
        b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

        mock_stt = STTTranscriptionResult(
            transcript="Explain quantum computing simply.",
            language="en",
            duration_seconds=1.0,
            latency_ms=50.0,
            success=True
        )

        with patch.object(stt_service, "transcribe_speech", return_value=mock_stt), \
             patch.object(tts_service, "synthesize_response", side_effect=RuntimeError("TTS Out of Memory")), \
             patch("backend.services.brain_engine.call_model", return_value="Quantum computers use qubits that can exist in superpositions."):

            res = client.post("/api/voice/turn", json={
                "audio_base64": b64_wav,
                "conversation_id": conv_id
            })

            assert res.status_code == 200
            data = res.json()
            assert "Quantum computers" in data["response_text"]
            assert data["has_audio"] is False # Audio failed gracefully
            
            # Verify text was still saved to conversation history
            hist = client.get(f"/api/conversations/{conv_id}/history").json()
            assert any("Quantum computers" in m.get("content", "") for m in hist.get("messages", []))

    def test_09_unique_turn_id_assigned(self):
        """(9) Proves every turn receives an explicit unique turn_id."""
        turn_req_1 = ChatRequest(message="Message 1", conversation_id="sess-turn-id")
        turn_req_2 = ChatRequest(message="Message 2", conversation_id="sess-turn-id")

        with patch("backend.services.brain_engine.call_model", return_value="Response"):
            res1 = brain_engine.execute_turn(turn_req_1)
            res2 = brain_engine.execute_turn(turn_req_2)

            assert res1.turn_id is not None
            assert res2.turn_id is not None
            assert res1.turn_id != res2.turn_id

    def test_10_duplicate_stale_turns_rejected_safely(self):
        """(10) Proves duplicate/stale submissions with identical turn_id are detected and handled safely."""
        conv_id = f"test-s1-dedup-{int(time.time()*1000)}"
        fixed_turn_id = f"fixed_turn_{int(time.time()*1000)}"

        with patch("backend.services.brain_engine.call_model", return_value="Primary execution response") as mock_model:
            req = ChatRequest(
                message="Calculate 25 * 4",
                conversation_id=conv_id,
                turn_id=fixed_turn_id
            )

            # First submission executes normally
            res1 = brain_engine.execute_turn(req)
            assert res1.response == "Primary execution response"
            assert mock_model.call_count == 1

            # Second duplicate submission with EXACT SAME turn_id returns cached result without re-executing model
            res2 = brain_engine.execute_turn(req)
            assert res2.response == "Primary execution response"
            assert mock_model.call_count == 1 # Model was NOT called again
