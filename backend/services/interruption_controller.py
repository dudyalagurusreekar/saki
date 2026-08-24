"""
Saki Real-Time Voice Interruption & Barge-In Controller (Sprint 9)

Coordinates natural conversational barge-in across local microphone, Silero VAD,
Kokoro TTS synthesis, and audio playback:
1. Detects genuine user speech onset while Saki is speaking or generating audio.
2. Filters transient acoustic spikes and noise via configurable chunk debounce.
3. Instantly halts active Kokoro TTS generation and in-memory audio playback (< 30ms).
4. Emits authoritative lifecycle events: INTERRUPTION_DETECTED, TTS_CANCELLED, LISTENING.
5. Manages conversational context integrity, preventing corrupted history or leaked resources.
6. Operates 100% locally with zero external network transmission.
"""

import time
import threading
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

from backend.core.events import SakiState, SakiEventType, SakiEvent
from backend.services.event_system import saki_event_manager
from backend.services.tts_service import tts_service, TTSLifecycleState


@dataclass
class InterruptionRecord:
    """Telemetry record for a single voice interruption event."""
    interruption_id: str
    conversation_id: str
    request_id: str
    timestamp: float
    reaction_latency_ms: float
    trigger_source: str = "vad_speech_onset"
    interrupted_state: str = "SPEAKING"
    interrupted_text: Optional[str] = None
    played_duration_sec: float = 0.0
    total_duration_sec: float = 0.0
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interruption_id": self.interruption_id,
            "conversation_id": self.conversation_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "reaction_latency_ms": round(self.reaction_latency_ms, 2),
            "trigger_source": self.trigger_source,
            "interrupted_state": self.interrupted_state,
            "interrupted_text": self.interrupted_text,
            "played_duration_sec": round(self.played_duration_sec, 3),
            "total_duration_sec": round(self.total_duration_sec, 3),
            "success": self.success
        }


@dataclass
class InterruptionTelemetry:
    """Runtime health, metrics, and configuration for the interruption controller."""
    enabled: bool = True
    is_interrupting: bool = False
    total_interruptions: int = 0
    avg_reaction_latency_ms: float = 0.0
    min_speech_duration_ms: float = 120.0
    min_consecutive_chunks: int = 3
    vad_threshold: float = 0.5
    last_interruption: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "is_interrupting": self.is_interrupting,
            "total_interruptions": self.total_interruptions,
            "avg_reaction_latency_ms": round(self.avg_reaction_latency_ms, 2),
            "min_speech_duration_ms": self.min_speech_duration_ms,
            "min_consecutive_chunks": self.min_consecutive_chunks,
            "vad_threshold": self.vad_threshold,
            "last_interruption": self.last_interruption
        }


class InterruptionController:
    """
    Authoritative Interruption & Barge-In Coordinator for Saki.
    Monitors speech onset and manages instant audio cancellation and lifecycle transitions.
    """
    _instance: Optional["InterruptionController"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(InterruptionController, cls).__new__(cls)
                cls._instance._init_controller()
            return cls._instance

    def _init_controller(self):
        self.enabled: bool = True
        self.min_speech_duration_ms: float = 120.0 # 3 chunks * 32ms = 96ms ~ 120ms
        self.min_consecutive_chunks: int = 3
        self.vad_threshold: float = 0.5

        self.total_interruptions: int = 0
        self._reaction_latencies: List[float] = []
        self._history: List[InterruptionRecord] = []
        self._last_record: Optional[InterruptionRecord] = None
        self._last_interruption_timestamp: float = 0.0

        # Debounce tracking
        self._consecutive_speech_chunks: int = 0
        self._candidate_speech_start_time: float = 0.0

        # State lock
        self._controller_lock = threading.RLock()

        # Interrupted turn context cache (conversation_id -> dict)
        self._interrupted_contexts: Dict[str, Dict[str, Any]] = {}

    def is_saki_speaking(self, conversation_id: str = "voice-session") -> bool:
        """
        Determines if Saki is currently in an interruptible state (synthesizing or playing speech).
        """
        if tts_service.playback_manager.is_playing():
            return True

        if tts_service.current_lifecycle_state in (
            TTSLifecycleState.TTS_PLAYING,
            TTSLifecycleState.TTS_GENERATING
        ):
            return True

        if saki_event_manager is not None:
            current_state = saki_event_manager.get_current_state(conversation_id)
            if current_state in (SakiState.SPEAKING, SakiState.PROCESSING):
                return True

        return False

    def evaluate_vad_chunk(
        self,
        speech_prob: float,
        is_speech: bool,
        conversation_id: str = "voice-session"
    ) -> bool:
        """
        Evaluates a single 32ms VAD chunk against debounce rules.
        Returns True if a genuine barge-in interruption was triggered, False otherwise.
        """
        if not self.enabled:
            return False

        with self._controller_lock:
            # Check if this chunk meets the speech probability criteria
            meets_threshold = is_speech or (speech_prob >= self.vad_threshold)

            if meets_threshold:
                self._consecutive_speech_chunks += 1
                if self._consecutive_speech_chunks == 1:
                    self._candidate_speech_start_time = time.perf_counter()

                # Check if speech duration has exceeded the debounce threshold
                speech_elapsed_ms = (time.perf_counter() - self._candidate_speech_start_time) * 1000.0
                debounce_met = (
                    self._consecutive_speech_chunks >= self.min_consecutive_chunks or
                    speech_elapsed_ms >= self.min_speech_duration_ms
                )

                if debounce_met and self.is_saki_speaking(conversation_id):
                    # Prevent rapid re-triggering within 100ms
                    if time.time() - self._last_interruption_timestamp > 0.10:
                        self.trigger_interruption(
                            conversation_id=conversation_id,
                            reason="user_speech_detected",
                            source="vad_speech_onset"
                        )
                        return True
            else:
                # Reset debounce on silence / noise dip
                self._consecutive_speech_chunks = 0

        return False

    def trigger_interruption(
        self,
        conversation_id: str = "voice-session",
        reason: str = "user_speech_detected",
        source: str = "vad_speech_onset"
    ) -> InterruptionRecord:
        """
        Executes immediate speech cancellation and transitions Saki to LISTENING.
        """
        t0 = time.perf_counter()
        now = time.time()
        intr_id = f"intr_{int(now * 1000)}"
        req_id = f"req_intr_{int(now * 1000)}"

        with self._controller_lock:
            self._last_interruption_timestamp = now
            self._consecutive_speech_chunks = 0

            # 1. Stop active speech synthesis and halt in-memory playback immediately (<30ms)
            tts_service.cancel_active_speech()

            reaction_ms = (time.perf_counter() - t0) * 1000.0

            # 2. Emit INTERRUPTION_DETECTED Event
            if saki_event_manager is not None:
                try:
                    saki_event_manager.emit(SakiEvent(
                        event_type=SakiEventType.INTERRUPTION,
                        conversation_id=conversation_id,
                        request_id=req_id,
                        state=SakiState.SPEAKING,
                        activity="User voice interruption detected. Halting speech output...",
                        capability="VOICE_INTERRUPTION",
                        details={
                            "event_name": "INTERRUPTION_DETECTED",
                            "trigger_source": source,
                            "reason": reason,
                            "reaction_latency_ms": round(reaction_ms, 2)
                        }
                    ))
                except Exception:
                    pass

                # 3. Emit TTS_CANCELLED Event
                try:
                    saki_event_manager.emit(SakiEvent(
                        event_type=SakiEventType.INTERRUPTION,
                        conversation_id=conversation_id,
                        request_id=req_id,
                        state=SakiState.SPEAKING,
                        activity="TTS audio playback successfully cancelled.",
                        capability="VOICE_INTERRUPTION",
                        details={
                            "event_name": "TTS_CANCELLED",
                            "reaction_latency_ms": round(reaction_ms, 2)
                        }
                    ))
                except Exception:
                    pass

                # 4. Transition to SakiState.LISTENING
                try:
                    saki_event_manager.transition(
                        conversation_id=conversation_id,
                        request_id=req_id,
                        new_state=SakiState.LISTENING,
                        activity="Listening to user speech...",
                        capability="VOICE_INTERRUPTION",
                        details={
                            "interrupted": True,
                            "reaction_latency_ms": round(reaction_ms, 2)
                        }
                    )
                except Exception:
                    pass

            # 5. Record telemetry
            record = InterruptionRecord(
                interruption_id=intr_id,
                conversation_id=conversation_id,
                request_id=req_id,
                timestamp=now,
                reaction_latency_ms=reaction_ms,
                trigger_source=source,
                interrupted_state="SPEAKING",
                success=True
            )

            self.total_interruptions += 1
            self._reaction_latencies.append(reaction_ms)
            if len(self._reaction_latencies) > 50:
                self._reaction_latencies.pop(0)

            self._last_record = record
            self._history.append(record)
            if len(self._history) > 50:
                self._history.pop(0)

            return record

    def record_interrupted_context(
        self,
        conversation_id: str,
        turn_text: str,
        total_audio_sec: float,
        played_sec: float
    ):
        """Stores metadata about the interrupted response for context continuity."""
        with self._controller_lock:
            self._interrupted_contexts[conversation_id] = {
                "interrupted_text": turn_text,
                "total_duration_sec": total_audio_sec,
                "played_duration_sec": played_sec,
                "timestamp": time.time()
            }

    def get_last_interrupted_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the last interrupted turn metadata for a conversation."""
        with self._controller_lock:
            return self._interrupted_contexts.get(conversation_id)

    def get_telemetry(self) -> InterruptionTelemetry:
        """Returns runtime telemetry for the interruption controller."""
        with self._controller_lock:
            avg_lat = (
                sum(self._reaction_latencies) / len(self._reaction_latencies)
                if self._reaction_latencies
                else 0.0
            )
            is_int = (time.time() - self._last_interruption_timestamp < 1.0)

            return InterruptionTelemetry(
                enabled=self.enabled,
                is_interrupting=is_int,
                total_interruptions=self.total_interruptions,
                avg_reaction_latency_ms=avg_lat,
                min_speech_duration_ms=self.min_speech_duration_ms,
                min_consecutive_chunks=self.min_consecutive_chunks,
                vad_threshold=self.vad_threshold,
                last_interruption=self._last_record.to_dict() if self._last_record else None
            )

    def update_config(
        self,
        enabled: Optional[bool] = None,
        min_speech_duration_ms: Optional[float] = None,
        min_consecutive_chunks: Optional[int] = None,
        vad_threshold: Optional[float] = None
    ) -> InterruptionTelemetry:
        """Updates runtime configuration."""
        with self._controller_lock:
            if enabled is not None:
                self.enabled = enabled
            if min_speech_duration_ms is not None:
                self.min_speech_duration_ms = max(10.0, min_speech_duration_ms)
            if min_consecutive_chunks is not None:
                self.min_consecutive_chunks = max(1, min_consecutive_chunks)
            if vad_threshold is not None:
                self.vad_threshold = max(0.01, min(1.0, vad_threshold))

            return self.get_telemetry()


# Global Singleton Instance
interruption_controller = InterruptionController()
