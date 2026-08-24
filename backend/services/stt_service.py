"""
Saki Local Speech-to-Text (STT) Service (Sprint 7 & 8)

Provides local, low-latency neural speech recognition using faster-whisper (CTranslate2).
Operates 100% locally with zero external network transmission.

Core Responsibilities:
1. In-memory audio transcription from binary WAV bytes, SpeechSegment, or numpy float32 arrays.
2. Fast CPU inference using 8-bit quantized models (tiny.en / base.en).
3. Graceful silence, noise rejection, and empty audio recovery.
4. Telemetry tracking: initialization time, transcription latency, RTF, CPU%, RAM, and word count.
5. Thread-safe execution and Saki Unified Event System lifecycle integration.
"""

import os
import io
import time
import threading
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, field

import numpy as np
import soundfile as sf

# Faster-Whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except Exception:
    WhisperModel = None
    FASTER_WHISPER_AVAILABLE = False

# Hardware monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

# Saki Unified Event System
try:
    from backend.core.events import SakiState, SakiEventType, SakiEvent
    from backend.services.event_system import saki_event_manager
    EVENTS_AVAILABLE = True
except ImportError:
    saki_event_manager = None
    EVENTS_AVAILABLE = False


@dataclass
class STTTranscriptionResult:
    """Represents the structured output of an in-memory speech recognition operation."""
    transcript: str = ""
    language: str = "en"
    language_probability: float = 1.0
    duration_seconds: float = 0.0
    latency_ms: float = 0.0
    rtf: float = 0.0
    model_name: str = "faster-whisper-tiny.en"
    device: str = "cpu"
    compute_type: str = "int8"
    word_count: int = 0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript": self.transcript,
            "language": self.language,
            "language_probability": round(self.language_probability, 3),
            "duration_seconds": round(self.duration_seconds, 3),
            "latency_ms": round(self.latency_ms, 2),
            "rtf": round(self.rtf, 3),
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "word_count": self.word_count,
            "segments_count": len(self.segments),
            "success": self.success,
            "error": self.error
        }


@dataclass
class STTTelemetry:
    """Runtime health, model status, and performance telemetry for the STT subsystem."""
    model_name: str = "faster-whisper-tiny.en"
    is_loaded: bool = False
    init_time_ms: float = 0.0
    device: str = "cpu"
    compute_type: str = "int8"
    total_transcriptions: int = 0
    avg_latency_ms: float = 0.0
    avg_rtf: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    last_transcript: str = ""
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "init_time_ms": round(self.init_time_ms, 2),
            "device": self.device,
            "compute_type": self.compute_type,
            "total_transcriptions": self.total_transcriptions,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_rtf": round(self.avg_rtf, 3),
            "cpu_percent": round(self.cpu_percent, 1),
            "memory_mb": round(self.memory_mb, 1),
            "last_transcript": self.last_transcript,
            "last_error": self.last_error
        }


class FasterWhisperSTTProvider:
    """
    Encapsulates faster-whisper neural speech recognition with CTranslate2 backend.
    """

    def __init__(
        self,
        model_size_or_path: Optional[str] = None,
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4
    ):
        self.model_size = model_size_or_path or os.environ.get("STT_MODEL_SIZE", "base")
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads

        self._model: Optional[Any] = None
        self._is_initialized = False
        self._init_error: Optional[str] = None
        self._lock = threading.Lock()
        self.init_time_ms: float = 0.0

    def initialize(self) -> bool:
        """Loads the faster-whisper neural model into memory."""
        with self._lock:
            if self._is_initialized and self._model is not None:
                return True

            if not FASTER_WHISPER_AVAILABLE:
                self._init_error = "faster-whisper is not installed or available."
                return False

            t0 = time.perf_counter()
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=self.cpu_threads
                )
                self._is_initialized = True
                self.init_time_ms = (time.perf_counter() - t0) * 1000.0
                self._init_error = None
                return True
            except Exception as e:
                # Fallback to float32 if int8 is not supported
                try:
                    self._model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type="float32",
                        cpu_threads=self.cpu_threads
                    )
                    self.compute_type = "float32"
                    self._is_initialized = True
                    self.init_time_ms = (time.perf_counter() - t0) * 1000.0
                    self._init_error = None
                    return True
                except Exception as e2:
                    self._init_error = f"Failed to initialize Faster-Whisper: {str(e2)}"
                    self._is_initialized = False
                    return False

    def is_available(self) -> bool:
        return self._is_initialized and self._model is not None

    def transcribe(
        self,
        audio_input: Union[bytes, np.ndarray, Any],
        language: str = "en",
        beam_size: int = 1,
        temperature: float = 0.0,
        vad_filter: bool = False
    ) -> STTTranscriptionResult:
        """
        Transcribes 16kHz audio input in memory.
        Accepts:
            - WAV bytes (bytes)
            - float32 numpy array [-1.0, 1.0] (np.ndarray)
            - SpeechSegment object with .audio_bytes or .raw_samples
        """
        t0 = time.perf_counter()

        if not self._is_initialized:
            if not self.initialize():
                return STTTranscriptionResult(
                    success=False,
                    error=self._init_error or "STT model not initialized",
                    latency_ms=(time.perf_counter() - t0) * 1000.0
                )

        # 1. Parse and normalize audio array to 16kHz float32
        try:
            audio_samples, duration_sec = self._extract_audio_samples(audio_input)
        except Exception as e:
            return STTTranscriptionResult(
                success=False,
                error=f"Audio decoding failed: {str(e)}",
                latency_ms=(time.perf_counter() - t0) * 1000.0
            )

        # 2. Check for empty or near-silent audio
        if len(audio_samples) == 0 or duration_sec < 0.1:
            return STTTranscriptionResult(
                transcript="",
                language=language,
                duration_seconds=duration_sec,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                rtf=0.0,
                model_name=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                word_count=0,
                success=True
            )

        # Check RMS energy
        rms = float(np.sqrt(np.mean(audio_samples ** 2)))
        if rms < 0.0001:
            # Pure silence
            return STTTranscriptionResult(
                transcript="",
                language=language,
                duration_seconds=duration_sec,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                rtf=0.0,
                model_name=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                word_count=0,
                success=True
            )

        # 3. Execute transcription under lock
        with self._lock:
            try:
                segments_iter, info = self._model.transcribe(
                    audio_samples,
                    language=language if language != "auto" else None,
                    beam_size=beam_size,
                    temperature=temperature,
                    vad_filter=vad_filter
                )

                seg_list = []
                transcript_parts = []
                for seg in segments_iter:
                    text = seg.text.strip()
                    if text:
                        transcript_parts.append(text)
                        seg_list.append({
                            "id": seg.id,
                            "start": round(seg.start, 3),
                            "end": round(seg.end, 3),
                            "text": text,
                            "avg_logprob": round(seg.avg_logprob, 3),
                            "no_speech_prob": round(seg.no_speech_prob, 3)
                        })

                full_transcript = " ".join(transcript_parts).strip()
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                rtf = (elapsed_ms / 1000.0) / max(0.001, duration_sec)

                return STTTranscriptionResult(
                    transcript=full_transcript,
                    language=info.language if hasattr(info, "language") else language,
                    language_probability=float(info.language_probability) if hasattr(info, "language_probability") else 1.0,
                    duration_seconds=duration_sec,
                    latency_ms=elapsed_ms,
                    rtf=rtf,
                    model_name=self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    word_count=len(full_transcript.split()) if full_transcript else 0,
                    segments=seg_list,
                    success=True
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return STTTranscriptionResult(
                    transcript="",
                    duration_seconds=duration_sec,
                    latency_ms=elapsed_ms,
                    model_name=self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    success=False,
                    error=f"Transcription failed: {str(e)}"
                )

    def _extract_audio_samples(self, audio_input: Any) -> Tuple[np.ndarray, float]:
        """Extracts a 1D float32 numpy array and computes duration in seconds."""
        # 1. SpeechSegment object
        if hasattr(audio_input, "raw_samples") and isinstance(audio_input.raw_samples, np.ndarray):
            samples = audio_input.raw_samples.astype(np.float32)
            sr = getattr(audio_input, "sample_rate", 16000)
            if sr != 16000 and len(samples) > 0:
                samples = self._resample_to_16k(samples, sr)
            dur = len(samples) / 16000.0
            return samples, dur

        # 2. Raw 1D float32 numpy array
        if isinstance(audio_input, np.ndarray):
            if audio_input.ndim > 1:
                audio_input = audio_input.mean(axis=1) # downmix to mono
            samples = audio_input.astype(np.float32)
            dur = len(samples) / 16000.0
            return samples, dur

        # 3. Binary WAV / audio bytes
        if isinstance(audio_input, (bytes, bytearray)):
            if len(audio_input) == 0:
                return np.zeros(0, dtype=np.float32), 0.0
            # Strategy A: soundfile library
            try:
                buf = io.BytesIO(audio_input)
                data, sr = sf.read(buf, dtype="float32")
                if data.ndim > 1:
                    data = data.mean(axis=1) # downmix to mono
                if sr != 16000:
                    data = self._resample_to_16k(data, sr)
                dur = len(data) / 16000.0
                return data.astype(np.float32), dur
            except Exception as e1:
                # Strategy B: standard library wave module (pure PCM WAV)
                try:
                    import wave
                    with wave.open(io.BytesIO(audio_input), 'rb') as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        framerate = wf.getframerate()
                        nframes = wf.getnframes()
                        raw_frames = wf.readframes(nframes)

                        if sampwidth == 2:
                            data = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
                        elif sampwidth == 4:
                            data = np.frombuffer(raw_frames, dtype=np.int32).astype(np.float32) / 2147483648.0
                        else:
                            data = (np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0

                        if channels > 1:
                            data = data.reshape(-1, channels).mean(axis=1)
                        if framerate != 16000:
                            data = self._resample_to_16k(data, framerate)
                        dur = len(data) / 16000.0
                        return data.astype(np.float32), dur
                except Exception as e2:
                    # Strategy C: raw int16 PCM array if headerless
                    if len(audio_input) % 2 == 0:
                        try:
                            raw_data = np.frombuffer(audio_input, dtype=np.int16).astype(np.float32) / 32768.0
                            dur = len(raw_data) / 16000.0
                            if dur > 0.1:
                                return raw_data, dur
                        except Exception:
                            pass

                    raise ValueError(f"Audio decoding failed: soundfile error ({e1}), wave error ({e2})")

        # 4. File path string
        if isinstance(audio_input, str) and os.path.exists(audio_input):
            data, sr = sf.read(audio_input, dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            if sr != 16000:
                data = self._resample_to_16k(data, sr)
            dur = len(data) / 16000.0
            return data.astype(np.float32), dur

        raise ValueError(f"Unsupported audio input type: {type(audio_input)}")

    @staticmethod
    def _resample_to_16k(audio: np.ndarray, original_sr: int) -> np.ndarray:
        if original_sr == 16000:
            return audio
        target_len = int(len(audio) * 16000 / float(original_sr))
        return np.interp(
            np.linspace(0, len(audio), target_len, endpoint=False),
            np.arange(len(audio)),
            audio
        ).astype(np.float32)


class STTServiceManager:
    """
    Central Singleton STT Service Coordinator.
    Manages provider lifecycle, telemetry aggregation, and event system notifications
    for English, Telugu, Kannada, and code-mixed speech recognition.
    """

    def __init__(self, provider: Optional[FasterWhisperSTTProvider] = None):
        self.provider = provider or FasterWhisperSTTProvider()
        self._latencies: List[float] = []
        self._rtfs: List[float] = []
        self.total_transcriptions = 0
        self.last_transcript = ""
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        return self.provider.initialize()

    def is_available(self) -> bool:
        return self.provider.is_available()

    def transcribe_speech(
        self,
        audio_input: Any,
        conversation_id: str = "voice-session",
        request_id: Optional[str] = None,
        language: str = "en"
    ) -> STTTranscriptionResult:
        """
        Transcribes audio and emits Saki Unified Events.
        """
        req_id = request_id or f"stt_{time.time()}"

        # Emit TRANSCRIBING event
        if EVENTS_AVAILABLE and saki_event_manager is not None:
            try:
                saki_event_manager.transition(
                    conversation_id=conversation_id,
                    request_id=req_id,
                    new_state=SakiState.PROCESSING,
                    activity="Transcribing user speech (STT)...",
                    capability="SPEECH_TO_TEXT",
                    details={"language": language, "stt_model": self.provider.model_size}
                )
            except Exception:
                pass

        result = self.provider.transcribe(audio_input, language=language)

        with self._lock:
            self.total_transcriptions += 1
            self.last_transcript = result.transcript
            self.last_error = result.error
            if result.success and result.duration_seconds > 0.1:
                self._latencies.append(result.latency_ms)
                self._rtfs.append(result.rtf)
                if len(self._latencies) > 50:
                    self._latencies.pop(0)
                    self._rtfs.pop(0)

        return result

    def get_telemetry(self) -> STTTelemetry:
        """Collects real-time STT subsystem telemetry and resource metrics."""
        cpu_pct = 0.0
        mem_mb = 0.0
        if PSUTIL_AVAILABLE and psutil is not None:
            try:
                proc = psutil.Process()
                cpu_pct = proc.cpu_percent(interval=None)
                mem_mb = proc.memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        avg_lat = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        avg_rtf = sum(self._rtfs) / len(self._rtfs) if self._rtfs else 0.0

        return STTTelemetry(
            model_name=self.provider.model_size,
            is_loaded=self.provider.is_available(),
            init_time_ms=self.provider.init_time_ms,
            device=self.provider.device,
            compute_type=self.provider.compute_type,
            total_transcriptions=self.total_transcriptions,
            avg_latency_ms=avg_lat,
            avg_rtf=avg_rtf,
            cpu_percent=cpu_pct,
            memory_mb=mem_mb,
            last_transcript=self.last_transcript,
            last_error=self.last_error
        )


# Global Singleton STT Service Instance
stt_service = STTServiceManager()
