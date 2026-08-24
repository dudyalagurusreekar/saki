"""
Saki Microphone & Voice Activity Detection (VAD) Service (Sprint 6)

Provides local, non-blocking microphone audio capture and neural speech detection
using Silero VAD (v5/v6) and sounddevice.
Operates 100% locally with zero external network transmission.

Core Responsibilities:
1. Local microphone input enumeration, device selection, and permission error handling.
2. In-memory audio streaming (16kHz mono 16-bit / float32) via sounddevice.InputStream.
3. Neural Voice Activity Detection via Silero VAD (speech start, continuous speech, speech end).
4. Saki Unified Event System lifecycle integration (emits SakiState.LISTENING on speech start).
5. Aggregates clean, isolated speech segments (16kHz WAV in memory) ready for Sprint 7 STT.
6. Safe concurrency: atomic state transitions, timeout support, error recovery, and duplicate stream prevention.
7. Empirical hardware telemetry: initialization time, detection latency, CPU%, RAM, device metadata.
"""

import os
import io
import time
import wave
import threading
import queue
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field

import numpy as np

# Audio capture library
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    sd = None
    SOUNDDEVICE_AVAILABLE = False

# Neural VAD libraries
try:
    import torch
    import silero_vad
    SILERO_TORCH_AVAILABLE = True
except Exception:
    torch = None
    silero_vad = None
    SILERO_TORCH_AVAILABLE = False

try:
    import onnxruntime as rt
    ONNX_AVAILABLE = True
except Exception:
    rt = None
    ONNX_AVAILABLE = False

# Hardware monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

# Saki Unified Event System & Interruption Controller
try:
    from backend.core.events import SakiState, SakiEventType, SakiEvent
    from backend.services.event_system import saki_event_manager
    from backend.services.interruption_controller import interruption_controller
    EVENTS_AVAILABLE = True
except ImportError:
    saki_event_manager = None
    interruption_controller = None
    EVENTS_AVAILABLE = False


# ---------------------------------------------------------
# ENUMS & DATA MODELS
# ---------------------------------------------------------
class MicState(str, Enum):
    MIC_IDLE = "MIC_IDLE"
    LISTENING = "LISTENING"
    SPEECH_DETECTED = "SPEECH_DETECTED"
    SPEECH_ENDED = "SPEECH_ENDED"
    MIC_ERROR = "MIC_ERROR"


@dataclass
class SpeechSegment:
    """Represents a clean, isolated user speech segment in memory."""
    audio_bytes: bytes                  # 16kHz 16-bit Mono WAV bytes
    raw_samples: np.ndarray             # 1D float32 numpy array [-1.0, 1.0]
    sample_rate: int = 16000
    duration_seconds: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    sample_count: int = 0
    peak_amplitude: float = 0.0
    rms_energy: float = 0.0
    detection_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "duration_seconds": round(self.duration_seconds, 3),
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "sample_count": self.sample_count,
            "peak_amplitude": round(float(self.peak_amplitude), 4),
            "rms_energy": round(float(self.rms_energy), 4),
            "detection_latency_ms": round(self.detection_latency_ms, 2),
            "audio_size_bytes": len(self.audio_bytes)
        }


@dataclass
class MicTelemetry:
    """Live telemetry and health status for the microphone subsystem."""
    state: str = MicState.MIC_IDLE.value
    is_capturing: bool = False
    speech_detected: bool = False
    device_index: Optional[int] = None
    device_name: str = "Default"
    sample_rate: int = 16000
    vad_model: str = "Silero-VAD-v5"
    init_time_ms: float = 0.0
    avg_chunk_latency_ms: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    total_speech_segments: int = 0
    last_segment_duration_sec: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "is_capturing": self.is_capturing,
            "speech_detected": self.speech_detected,
            "device_index": self.device_index,
            "device_name": self.device_name,
            "sample_rate": self.sample_rate,
            "vad_model": self.vad_model,
            "init_time_ms": round(self.init_time_ms, 2),
            "avg_chunk_latency_ms": round(self.avg_chunk_latency_ms, 2),
            "cpu_percent": round(self.cpu_percent, 1),
            "memory_mb": round(self.memory_mb, 1),
            "total_speech_segments": self.total_speech_segments,
            "last_segment_duration_sec": round(self.last_segment_duration_sec, 3),
            "error": self.error
        }


# ---------------------------------------------------------
# AUDIO CONVERSION HELPERS
# ---------------------------------------------------------
def float32_to_wav_bytes(samples: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Converts a 1D float32 numpy array [-1.0, 1.0] to in-memory 16-bit linear PCM WAV bytes."""
    samples_clamped = np.clip(samples, -1.0, 1.0)
    int16_samples = (samples_clamped * 32767.0).astype(np.int16)
    
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(int16_samples.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------
# SILERO VAD DETECTOR
# ---------------------------------------------------------
class SileroVADDetector:
    """
    Encapsulates Silero VAD (v5/v6) neural network for fast, chunk-level
    voice activity detection on 16kHz audio.
    """

    def __init__(
        self,
        onnx_model_path: Optional[str] = None,
        threshold: float = 0.5,
        min_silence_duration_ms: int = 500,
        speech_pad_ms: int = 30
    ):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.onnx_model_path = onnx_model_path or os.path.join(base_dir, "models", "vad", "silero_vad.onnx")
        self.threshold = threshold
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms

        self._torch_model = None
        self._vad_iterator = None
        self._onnx_session = None
        self._onnx_state = None
        self._is_initialized = False
        self._init_error = None
        self._lock = threading.Lock()
        self.init_time_ms = 0.0

    def initialize(self) -> bool:
        with self._lock:
            if self._is_initialized:
                return True

            t0 = time.perf_counter()
            try:
                # 1. Preferred mode: Torch JIT Silero VAD (fastest & native VADIterator support)
                if SILERO_TORCH_AVAILABLE:
                    self._torch_model = silero_vad.load_silero_vad()
                    self._vad_iterator = silero_vad.VADIterator(
                        self._torch_model,
                        threshold=self.threshold,
                        sampling_rate=16000,
                        min_silence_duration_ms=self.min_silence_duration_ms,
                        speech_pad_ms=self.speech_pad_ms
                    )
                    self._is_initialized = True
                    self.init_time_ms = (time.perf_counter() - t0) * 1000.0
                    return True

                # 2. Fallback mode: Direct ONNXRuntime session
                if ONNX_AVAILABLE and os.path.exists(self.onnx_model_path):
                    with open(self.onnx_model_path, "rb") as f:
                        model_bytes = f.read()
                    self._onnx_session = rt.InferenceSession(model_bytes, providers=["CPUExecutionProvider"])
                    self._onnx_state = np.zeros((2, 1, 128), dtype=np.float32)
                    self._is_initialized = True
                    self.init_time_ms = (time.perf_counter() - t0) * 1000.0
                    return True

                self._init_error = "Neither silero-vad/torch nor onnxruntime model could be loaded."
                return False
            except Exception as e:
                self._init_error = f"Failed to initialize Silero VAD: {str(e)}"
                self._is_initialized = False
                return False

    def reset_state(self):
        """Resets the internal recurrence/iterator states for a new listening turn."""
        with self._lock:
            if self._vad_iterator is not None:
                self._vad_iterator.reset_states()
            if self._onnx_session is not None:
                self._onnx_state = np.zeros((2, 1, 128), dtype=np.float32)

    def is_available(self) -> bool:
        return self._is_initialized or SILERO_TORCH_AVAILABLE or (ONNX_AVAILABLE and os.path.exists(self.onnx_model_path))

    def get_speech_probability(self, chunk_samples: np.ndarray) -> float:
        """
        Computes the speech probability [0.0 - 1.0] for a 512-sample (32ms) 16kHz audio chunk.
        """
        if not self._is_initialized:
            if not self.initialize():
                return 0.0

        with self._lock:
            try:
                # 1. Torch Path
                if self._torch_model is not None:
                    if isinstance(chunk_samples, np.ndarray):
                        chunk_tensor = torch.from_numpy(chunk_samples).float()
                    else:
                        chunk_tensor = chunk_samples
                    if chunk_tensor.ndim == 1:
                        if len(chunk_tensor) != 512:
                            # Pad or slice to 512
                            if len(chunk_tensor) < 512:
                                chunk_tensor = torch.nn.functional.pad(chunk_tensor, (0, 512 - len(chunk_tensor)))
                            else:
                                chunk_tensor = chunk_tensor[:512]
                    prob = self._torch_model(chunk_tensor, 16000).item()
                    return float(prob)

                # 2. ONNX Path
                if self._onnx_session is not None:
                    chunk_arr = np.asarray(chunk_samples, dtype=np.float32)
                    if len(chunk_arr) < 512:
                        chunk_arr = np.pad(chunk_arr, (0, 512 - len(chunk_arr)))
                    elif len(chunk_arr) > 512:
                        chunk_arr = chunk_arr[:512]
                    chunk_in = chunk_arr.reshape(1, 512)
                    sr_in = np.array(16000, dtype=np.int64)

                    out, self._onnx_state = self._onnx_session.run(
                        None,
                        {"input": chunk_in, "state": self._onnx_state, "sr": sr_in}
                    )
                    return float(out[0][0])
            except Exception:
                return 0.0

        return 0.0

    def process_chunk(self, chunk_samples: np.ndarray) -> Tuple[float, Optional[Dict[str, int]]]:
        """
        Processes a 512-sample audio chunk.
        Returns:
            (speech_probability, vad_event_dict_or_None)
            where vad_event_dict is e.g. {'start': sample_idx} or {'end': sample_idx}.
        """
        if not self._is_initialized:
            if not self.initialize():
                return 0.0, None

        prob = self.get_speech_probability(chunk_samples)
        vad_event = None

        with self._lock:
            if self._vad_iterator is not None:
                try:
                    if isinstance(chunk_samples, np.ndarray):
                        chunk_t = torch.from_numpy(chunk_samples).float()
                    else:
                        chunk_t = chunk_samples
                    if len(chunk_t) != 512:
                        if len(chunk_t) < 512:
                            chunk_t = torch.nn.functional.pad(chunk_t, (0, 512 - len(chunk_t)))
                        else:
                            chunk_t = chunk_t[:512]
                    vad_event = self._vad_iterator(chunk_t)
                except Exception:
                    vad_event = None

        return prob, vad_event


# ---------------------------------------------------------
# MICROPHONE MANAGER
# ---------------------------------------------------------
class MicrophoneManager:
    """
    Manages local hardware microphone input capture, audio buffering,
    Silero VAD speech detection lifecycle, and Saki Event System transitions.
    """

    def __init__(
        self,
        vad_detector: Optional[SileroVADDetector] = None,
        sample_rate: int = 16000,
        chunk_size: int = 512 # 512 samples @ 16kHz = 32ms
    ):
        self.vad = vad_detector or SileroVADDetector()
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.min_speech_chunks = 3  # ~96ms debounce threshold
        self.min_speech_duration_ms = 120.0

        self._selected_device_index: Optional[int] = None
        self._selected_device_name: str = "Default"
        self._stream: Optional[Any] = None
        self._is_capturing = False
        self._is_speech_active = False
        self._consecutive_speech_chunks = 0

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=200)

        # Buffers for active speech segment
        self._speech_buffer: List[np.ndarray] = []
        self._pre_speech_ring_buffer: List[np.ndarray] = []
        self._max_pre_speech_chunks = 10 # ~320ms lookback

        # Last completed speech segment
        self.latest_speech_segment: Optional[SpeechSegment] = None
        self.total_speech_segments = 0

        # State tracking
        self.current_state = MicState.MIC_IDLE
        self.last_error: Optional[str] = None

        # Telemetry metrics
        self.latest_chunk_latency_ms: float = 0.0
        self._latency_samples: List[float] = []

    # -----------------------------------------------------
    # DEVICE ENUMERATION & SELECTION
    # -----------------------------------------------------
    def list_devices(self) -> List[Dict[str, Any]]:
        """Enumerates available local audio input devices."""
        if not SOUNDDEVICE_AVAILABLE:
            return []

        devices = []
        try:
            default_input_idx = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else None
            all_devs = sd.query_devices()

            for idx, dev in enumerate(all_devs):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append({
                        "id": idx,
                        "name": dev.get("name", f"Device {idx}"),
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 16000.0),
                        "is_default": idx == default_input_idx
                    })
        except Exception as e:
            self.last_error = f"Failed to query audio devices: {str(e)}"
        return devices

    def set_device(self, device_id: Optional[int]) -> bool:
        """Sets the active input microphone device."""
        with self._lock:
            if self._is_capturing:
                return False # Cannot switch device while capturing

            self._selected_device_index = device_id
            if device_id is not None and SOUNDDEVICE_AVAILABLE:
                try:
                    dev_info = sd.query_devices(device_id)
                    self._selected_device_name = dev_info.get("name", f"Device {device_id}")
                except Exception:
                    self._selected_device_name = f"Device {device_id}"
            else:
                self._selected_device_name = "Default"
            return True

    # -----------------------------------------------------
    # LIFECYCLE: START & STOP LISTENING
    # -----------------------------------------------------
    def start_listening(
        self,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[SpeechSegment], None]] = None,
        timeout_seconds: Optional[float] = None
    ) -> bool:
        """
        Starts non-blocking background microphone capture and VAD detection loop.
        """
        with self._lock:
            if self._is_capturing:
                return True # Already listening, protect against duplicate streams

            if not SOUNDDEVICE_AVAILABLE:
                self.last_error = "sounddevice is not installed or available."
                self.current_state = MicState.MIC_ERROR
                return False

            # Initialize VAD
            if not self.vad.initialize():
                self.last_error = self.vad._init_error or "Failed to initialize Silero VAD."
                self.current_state = MicState.MIC_ERROR
                return False

            self.vad.reset_state()
            self._stop_event.clear()
            self._audio_queue = queue.Queue(maxsize=200)
            self._speech_buffer.clear()
            self._pre_speech_ring_buffer.clear()
            self._is_speech_active = False

            # Create audio input stream callback
            def audio_callback(indata, frames, time_info, status):
                if status:
                    # Non-fatal overflow or underflow
                    pass
                if not self._stop_event.is_set():
                    # Extract mono float32 array
                    chunk = indata[:, 0].copy()
                    try:
                        self._audio_queue.put_nowait(chunk)
                    except queue.Full:
                        pass # Drop chunk if consumer is backed up

            try:
                self._stream = sd.InputStream(
                    device=self._selected_device_index,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.chunk_size,
                    callback=audio_callback
                )
                self._stream.start()
            except Exception as e:
                self.last_error = f"Failed to open microphone stream: {str(e)}"
                self.current_state = MicState.MIC_ERROR
                return False

            self._is_capturing = True
            self.current_state = MicState.LISTENING
            self.last_error = None

            # Spawn background VAD processing worker
            self._worker_thread = threading.Thread(
                target=self._vad_worker_loop,
                args=(on_speech_start, on_speech_end, timeout_seconds),
                daemon=True,
                name="Saki-Microphone-VAD-Worker"
            )
            self._worker_thread.start()

            return True

    def stop_listening(self) -> bool:
        """Safely stops microphone capture and releases the hardware device."""
        with self._lock:
            if not self._is_capturing:
                return True

            self._stop_event.set()
            self._is_capturing = False
            self._is_speech_active = False

            # Stop and close stream
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            self.current_state = MicState.MIC_IDLE
            self.vad.reset_state()

        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

        return True

    # -----------------------------------------------------
    # BACKGROUND VAD PROCESSING WORKER
    # -----------------------------------------------------
    def _vad_worker_loop(
        self,
        on_speech_start: Optional[Callable[[], None]],
        on_speech_end: Optional[Callable[[SpeechSegment], None]],
        timeout_seconds: Optional[float]
    ):
        start_loop_time = time.perf_counter()
        speech_start_time = 0.0

        while not self._stop_event.is_set():
            # Check optional timeout
            if timeout_seconds and (time.perf_counter() - start_loop_time) > timeout_seconds:
                break

            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            t0 = time.perf_counter()
            prob, vad_event = self.vad.process_chunk(chunk)
            chunk_latency = (time.perf_counter() - t0) * 1000.0
            self.latest_chunk_latency_ms = chunk_latency
            self._latency_samples.append(chunk_latency)
            if len(self._latency_samples) > 50:
                self._latency_samples.pop(0)

            # -------------------------------------------------
            # SPEECH ONSET / CONTINUATION / END HANDLING (WITH DEBOUNCE)
            # -------------------------------------------------
            is_speech_chunk = (prob >= self.vad.threshold) or (vad_event and "start" in vad_event)
            is_speech_end = (vad_event and "end" in vad_event)

            # Check for real-time barge-in interruption while Saki is speaking
            if interruption_controller is not None and is_speech_chunk:
                try:
                    interruption_controller.evaluate_vad_chunk(
                        speech_prob=prob,
                        is_speech=is_speech_chunk,
                        conversation_id="voice-session"
                    )
                except Exception:
                    pass

            if not self._is_speech_active:
                # Maintain pre-speech ring buffer
                self._pre_speech_ring_buffer.append(chunk)
                if len(self._pre_speech_ring_buffer) > self._max_pre_speech_chunks:
                    self._pre_speech_ring_buffer.pop(0)

                if is_speech_chunk:
                    self._consecutive_speech_chunks += 1
                    # Debounce: require minimum consecutive speech chunks before confirming speech onset
                    if self._consecutive_speech_chunks >= self.min_speech_chunks or (vad_event and "start" in vad_event):
                        self._is_speech_active = True
                        self.current_state = MicState.SPEECH_DETECTED
                        speech_start_time = time.perf_counter()

                        # Include pre-speech context
                        self._speech_buffer = list(self._pre_speech_ring_buffer)
                        self._speech_buffer.append(chunk)

                        # Emit Unified Saki Event
                        if EVENTS_AVAILABLE and saki_event_manager is not None:
                            try:
                                saki_event_manager.transition(
                                    conversation_id="voice-session",
                                    request_id=f"mic_{time.time()}",
                                    new_state=SakiState.LISTENING,
                                    activity="User voice activity detected. Listening...",
                                    capability="MICROPHONE_INPUT",
                                    details={
                                        "speech_detected": True,
                                        "speech_probability": round(prob, 3),
                                        "device": self._selected_device_name
                                    }
                                )
                            except Exception:
                                pass

                        if on_speech_start:
                            try:
                                on_speech_start()
                            except Exception:
                                pass
                else:
                    # Reset debounce counter on silence
                    self._consecutive_speech_chunks = 0
            else:
                # Speech is actively underway
                self._speech_buffer.append(chunk)

                if is_speech_end or (len(self._speech_buffer) * self.chunk_size / self.sample_rate > 30.0): # Max 30s utterance
                    self._is_speech_active = False
                    self.current_state = MicState.SPEECH_ENDED
                    speech_end_time = time.perf_counter()

                    # Assemble complete speech segment
                    if self._speech_buffer:
                        full_samples = np.concatenate(self._speech_buffer)
                    else:
                        full_samples = np.zeros(0, dtype=np.float32)

                    dur_sec = len(full_samples) / float(self.sample_rate)
                    peak = float(np.max(np.abs(full_samples))) if len(full_samples) > 0 else 0.0
                    rms = float(np.sqrt(np.mean(full_samples ** 2))) if len(full_samples) > 0 else 0.0
                    wav_bytes = float32_to_wav_bytes(full_samples, self.sample_rate)

                    segment = SpeechSegment(
                        audio_bytes=wav_bytes,
                        raw_samples=full_samples,
                        sample_rate=self.sample_rate,
                        duration_seconds=dur_sec,
                        start_time=speech_start_time,
                        end_time=speech_end_time,
                        sample_count=len(full_samples),
                        peak_amplitude=peak,
                        rms_energy=rms,
                        detection_latency_ms=chunk_latency
                    )

                    self.latest_speech_segment = segment
                    self.total_speech_segments += 1
                    self._speech_buffer.clear()
                    self._pre_speech_ring_buffer.clear()

                    # Emit Unified Saki Event
                    if EVENTS_AVAILABLE and saki_event_manager is not None:
                        try:
                            saki_event_manager.transition(
                                conversation_id="voice-session",
                                request_id=f"mic_{time.time()}",
                                new_state=SakiState.IDLE,
                                activity="Speech segment completed and ready for processing.",
                                capability="MICROPHONE_INPUT",
                                details={
                                    "speech_ended": True,
                                    "duration_sec": round(dur_sec, 3),
                                    "sample_count": len(full_samples),
                                    "audio_bytes_size": len(wav_bytes)
                                }
                            )
                        except Exception:
                            pass

                    if on_speech_end:
                        try:
                            on_speech_end(segment)
                        except Exception:
                            pass

                    # Return to LISTENING for next utterance
                    self.current_state = MicState.LISTENING

    # -----------------------------------------------------
    # STATUS & TELEMETRY
    # -----------------------------------------------------
    def get_telemetry(self) -> MicTelemetry:
        """Gathers real-time hardware telemetry and status."""
        cpu_pct = 0.0
        mem_mb = 0.0
        if PSUTIL_AVAILABLE and psutil is not None:
            try:
                proc = psutil.Process()
                cpu_pct = proc.cpu_percent(interval=None)
                mem_mb = proc.memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        avg_latency = (
            sum(self._latency_samples) / len(self._latency_samples)
            if self._latency_samples
            else self.latest_chunk_latency_ms
        )

        last_dur = self.latest_speech_segment.duration_seconds if self.latest_speech_segment else 0.0

        return MicTelemetry(
            state=self.current_state.value,
            is_capturing=self._is_capturing,
            speech_detected=self._is_speech_active,
            device_index=self._selected_device_index,
            device_name=self._selected_device_name,
            sample_rate=self.sample_rate,
            vad_model="Silero-VAD-v5" if self.vad._torch_model or self.vad._onnx_session else "None",
            init_time_ms=self.vad.init_time_ms,
            avg_chunk_latency_ms=avg_latency,
            cpu_percent=cpu_pct,
            memory_mb=mem_mb,
            total_speech_segments=self.total_speech_segments,
            last_segment_duration_sec=last_dur,
            error=self.last_error
        )


# Global Singleton Service Instance
microphone_service = MicrophoneManager()
