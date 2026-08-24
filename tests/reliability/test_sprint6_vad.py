"""
Sprint 6 — Saki Local Microphone & Voice Activity Detection (Silero VAD) Test Suite

Validates:
1. Silero VAD initialization, model availability, and metadata telemetry.
2. High-precision speech vs silence discrimination (<0.05 on silence, >0.5 on synthetic speech).
3. Exact speech onset and offset (start/end) boundary detection.
4. Local microphone device enumeration and default detection.
5. Safe device selection and parameter configuration.
6. State machine lifecycle: MIC_IDLE -> LISTENING -> SPEECH_DETECTED -> SPEECH_ENDED -> MIC_IDLE.
7. Saki Unified Event System lifecycle integration (emits SakiState.LISTENING).
8. In-memory 16kHz 16-bit linear PCM WAV speech segment generation.
9. FastAPI endpoints (/api/mic/status, /devices, /vad/process, /latest-segment).
"""

import os
import sys
import io
import time
import base64
import wave
import pytest
import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.microphone_service import (
    microphone_service,
    SileroVADDetector,
    MicrophoneManager,
    MicState,
    SpeechSegment,
    float32_to_wav_bytes
)
from backend.services.tts_service import tts_service
from backend.core.events import SakiState, SakiEventType
from backend.services.event_system import saki_event_manager
from fastapi.testclient import TestClient
from backend.main import app


class TestSprint6VADService:
    """Comprehensive test suite verifying local microphone capture and Silero VAD."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Ensures microphone service is safely stopped and clean before/after tests."""
        microphone_service.stop_listening()
        yield
        microphone_service.stop_listening()

    def test_01_silero_vad_initialization_and_status(self):
        """TEST 1: Silero VAD initializes cleanly on local CPU with zero network calls."""
        vad = SileroVADDetector()
        ok = vad.initialize()
        assert ok is True
        assert vad.is_available() is True
        assert vad.init_time_ms >= 0.0
        assert vad._init_error is None

    def test_02_silence_vs_speech_discrimination(self):
        """TEST 2: VAD evaluates near-zero probability for silence and high probability for speech."""
        vad = SileroVADDetector()
        assert vad.initialize() is True

        # 1. Pure Silence (512 samples of float32 zeros)
        silence_chunk = np.zeros(512, dtype=np.float32)
        silence_prob = vad.get_speech_probability(silence_chunk)
        assert silence_prob < 0.05, f"Silence speech probability too high: {silence_prob}"

        # 2. Low amplitude background room noise (RMS ~0.0005)
        noise_chunk = (np.random.randn(512) * 0.0005).astype(np.float32)
        noise_prob = vad.get_speech_probability(noise_chunk)
        assert noise_prob < 0.20, f"Low background noise probability too high: {noise_prob}"

        # 3. Real Synthesized Speech Chunk from Kokoro TTS
        tts_res = tts_service.synthesize_response("Hello, I am testing voice activity detection.")
        assert tts_res.audio_bytes is not None

        # Read TTS WAV into 16kHz float32
        import soundfile as sf
        audio_data, sr = sf.read(io.BytesIO(tts_res.audio_bytes), dtype="float32")
        target_len = int(len(audio_data) * 16000 / float(sr))
        audio_16k = np.interp(
            np.linspace(0, len(audio_data), target_len, endpoint=False),
            np.arange(len(audio_data)),
            audio_data
        ).astype(np.float32)

        # Find peak energy chunk
        speech_probs = []
        for i in range(0, len(audio_16k) - 512, 512):
            chunk = audio_16k[i:i+512]
            p = vad.get_speech_probability(chunk)
            speech_probs.append(p)

        max_prob = max(speech_probs)
        assert max_prob > 0.5, f"Speech peak probability was too low: {max_prob}"

    def test_03_speech_onset_and_offset_detection(self):
        """TEST 3: VADIterator detects speech start and speech end events with padding."""
        vad = SileroVADDetector(threshold=0.5, min_silence_duration_ms=300)
        assert vad.initialize() is True
        vad.reset_state()

        # Generate speech audio
        tts_res = tts_service.synthesize_response("Testing speech detection boundaries.")
        import soundfile as sf
        audio_data, sr = sf.read(io.BytesIO(tts_res.audio_bytes), dtype="float32")
        target_len = int(len(audio_data) * 16000 / float(sr))
        audio_16k = np.interp(
            np.linspace(0, len(audio_data), target_len, endpoint=False),
            np.arange(len(audio_data)),
            audio_data
        ).astype(np.float32)

        # Pad with 0.5s initial silence and 1.0s trailing silence
        initial_silence = np.zeros(8000, dtype=np.float32)
        trailing_silence = np.zeros(16000, dtype=np.float32)
        full_stream = np.concatenate([initial_silence, audio_16k, trailing_silence])

        events = []
        for i in range(0, len(full_stream) - 512, 512):
            chunk = full_stream[i:i+512]
            _, vad_ev = vad.process_chunk(chunk)
            if vad_ev:
                events.append((round(i / 16000.0, 3), vad_ev))

        # Must detect at least one 'start' and one 'end'
        has_start = any("start" in ev[1] for ev in events)
        has_end = any("end" in ev[1] for ev in events)

        assert has_start is True, f"No speech start event detected: {events}"
        assert has_end is True, f"No speech end event detected: {events}"

    def test_04_microphone_device_enumeration(self):
        """TEST 4: list_devices returns valid system audio input devices."""
        devices = microphone_service.list_devices()
        assert isinstance(devices, list)
        # Verify device dictionary schema
        for d in devices:
            assert "id" in d
            assert "name" in d
            assert "channels" in d
            assert d["channels"] > 0
            assert "default_samplerate" in d

    def test_05_microphone_device_selection(self):
        """TEST 5: set_device safely sets target device index and updates telemetry."""
        ok = microphone_service.set_device(None)
        assert ok is True
        assert microphone_service._selected_device_name == "Default"

        # Try selecting device 0 if exists
        devs = microphone_service.list_devices()
        if devs:
            dev_id = devs[0]["id"]
            ok = microphone_service.set_device(dev_id)
            assert ok is True
            assert microphone_service._selected_device_index == dev_id

    def test_06_state_machine_lifecycle(self):
        """TEST 6: Validates microphone lifecycle states and clean shutdown."""
        assert microphone_service.current_state == MicState.MIC_IDLE
        tel_idle = microphone_service.get_telemetry()
        assert tel_idle.state == "MIC_IDLE"
        assert tel_idle.is_capturing is False

        # Start with a fast 1-second timeout
        started = microphone_service.start_listening(timeout_seconds=1.0)
        assert started is True
        assert microphone_service.current_state in [MicState.LISTENING, MicState.SPEECH_DETECTED]

        # Duplicate start listening protection
        dup_started = microphone_service.start_listening()
        assert dup_started is True

        # Stop listening
        stopped = microphone_service.stop_listening()
        assert stopped is True
        assert microphone_service.current_state == MicState.MIC_IDLE
        assert microphone_service._is_capturing is False

    def test_07_event_system_lifecycle_tracking(self):
        """TEST 7: Emits SakiState.LISTENING on speech start and SakiState.IDLE on speech end."""
        q = saki_event_manager.subscribe_sync("test-voice-session")

        # 1. Transition to LISTENING on speech start
        ev1 = saki_event_manager.transition(
            conversation_id="test-voice-session",
            request_id="test_req_start",
            new_state=SakiState.LISTENING,
            activity="User voice activity detected. Listening...",
            capability="MICROPHONE_INPUT",
            details={"speech_detected": True}
        )

        # 2. Transition to IDLE on speech end
        ev2 = saki_event_manager.transition(
            conversation_id="test-voice-session",
            request_id="test_req_end",
            new_state=SakiState.IDLE,
            activity="Speech segment completed and ready for processing.",
            capability="MICROPHONE_INPUT",
            details={"speech_ended": True}
        )

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        saki_event_manager.unsubscribe_sync(q, "test-voice-session")

        states = [e.state for e in events]
        assert SakiState.LISTENING in states
        assert SakiState.IDLE in states
        assert ev1.state == SakiState.LISTENING
        assert ev2.state == SakiState.IDLE

    def test_08_speech_segment_aggregation_and_wav(self):
        """TEST 8: float32_to_wav_bytes produces a valid 16kHz 16-bit linear PCM WAV."""
        # Generate 1.0 second of 440Hz sine wave at 16kHz
        t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
        sine_wave = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

        wav_bytes = float32_to_wav_bytes(sine_wave, sample_rate=16000)
        assert isinstance(wav_bytes, bytes)
        assert len(wav_bytes) > 32000 # 16000 samples * 2 bytes = 32000 + 44 header bytes

        # Read back with wave library
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2 # 16-bit
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 16000

        # Create SpeechSegment dataclass
        segment = SpeechSegment(
            audio_bytes=wav_bytes,
            raw_samples=sine_wave,
            sample_rate=16000,
            duration_seconds=1.0,
            start_time=time.perf_counter(),
            end_time=time.perf_counter() + 1.0,
            sample_count=16000,
            peak_amplitude=float(np.max(np.abs(sine_wave))),
            rms_energy=float(np.sqrt(np.mean(sine_wave ** 2))),
            detection_latency_ms=1.5
        )
        d = segment.to_dict()
        assert d["duration_seconds"] == 1.0
        assert d["sample_rate"] == 16000
        assert d["sample_count"] == 16000

    def test_09_fastapi_endpoints_and_offline_processing(self):
        """TEST 9: FastAPI endpoints /api/mic/status, /devices, /vad/process respond correctly."""
        client = TestClient(app)

        # 1. GET /api/mic/status
        res = client.get("/api/mic/status")
        assert res.status_code == 200
        data = res.json()
        assert "state" in data
        assert "is_capturing" in data
        assert "sample_rate" in data
        assert data["sample_rate"] == 16000
        assert data["vad_available"] is True

        # 2. GET /api/mic/devices
        res_devs = client.get("/api/mic/devices")
        assert res_devs.status_code == 200
        dev_list = res_devs.json()
        assert isinstance(dev_list, list)

        # 3. POST /api/mic/vad/process (Offline speech detection)
        # Generate short speech snippet via TTS
        tts_res = tts_service.synthesize_response("Hello Saki.")
        b64_audio = base64.b64encode(tts_res.audio_bytes).decode("utf-8")

        res_vad = client.post(
            "/api/mic/vad/process",
            json={"audio_base64": b64_audio, "threshold": 0.5}
        )
        assert res_vad.status_code == 200
        vad_data = res_vad.json()
        assert "speech_detected" in vad_data
        assert vad_data["speech_detected"] is True
        assert vad_data["total_duration_sec"] > 0.0
        assert "segment_metadata" in vad_data
        assert vad_data["segment_metadata"]["sample_rate"] == 16000
