"""
Saki Unified Voice Orchestrator (Sprint 8)

Coordinates the complete end-to-end voice conversation pipeline:
Microphone / VAD (Sprint 6) -> Faster-Whisper STT (Sprint 7/8) -> Existing Saki Cognitive Brain (chat/orchestrator/memory) -> Kokoro TTS (Sprint 5) -> Audio Output.

Operates 100% locally with zero external network transmission.
Ensures zero architectural bifurcation: voice requests use the exact same conversation context,
memory store, persona modulation, and model routing as text chat.
"""

import io
import time
import base64
import threading
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field

import numpy as np

# Core services
from backend.services.microphone_service import microphone_service, SpeechSegment, MicState
from backend.services.stt_service import stt_service, STTTranscriptionResult
from backend.services.tts_service import tts_service, TTSAudioResult, TTSLifecycleState
from backend.services.interruption_controller import interruption_controller, InterruptionRecord, InterruptionTelemetry
from backend.services.memory_service import load_memory, update_memory
from backend.services.multilingual_service import multilingual_service, LanguageProfile
from backend.routes.chat import ChatRequest, chat
from backend.core.config import settings

# Saki Unified Event System
try:
    from backend.core.events import SakiState, SakiEventType, SakiEvent
    from backend.services.event_system import saki_event_manager
    EVENTS_AVAILABLE = True
except ImportError:
    saki_event_manager = None
    EVENTS_AVAILABLE = False


@dataclass
class VoiceTurnResult:
    """Represents the complete result of a unified voice interaction turn."""
    transcript: str = ""
    response_text: str = ""
    conversation_id: str = "voice-session"
    request_id: str = ""
    selected_model: str = "phi3:latest"
    task_type: str = "casual_chat"
    conversation_mode: str = "casual"
    detected_language: str = "en"
    language_confidence: float = 1.0
    output_language: str = "en"
    language_profile: Dict[str, Any] = field(default_factory=dict)
    audio_bytes: Optional[bytes] = None
    audio_base64: Optional[str] = None
    audio_duration_sec: float = 0.0
    voice_used: str = "af_heart"
    tts_provider: str = "kokoro"
    stt_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    memory_count: int = 0
    interrupted: bool = False
    interrupted_at_sec: float = 0.0
    success: bool = True
    error: Optional[str] = None

    @property
    def has_audio(self) -> bool:
        return self.audio_bytes is not None and len(self.audio_bytes) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript": self.transcript,
            "response_text": self.response_text,
            "conversation_id": self.conversation_id,
            "request_id": self.request_id,
            "selected_model": self.selected_model,
            "task_type": self.task_type,
            "conversation_mode": self.conversation_mode,
            "detected_language": self.detected_language,
            "language_confidence": round(self.language_confidence, 3),
            "output_language": self.output_language,
            "language_profile": self.language_profile,
            "has_audio": self.audio_bytes is not None and len(self.audio_bytes) > 0,
            "audio_duration_sec": round(self.audio_duration_sec, 3),
            "voice_used": self.voice_used,
            "tts_provider": self.tts_provider,
            "interrupted": self.interrupted,
            "interrupted_at_sec": round(self.interrupted_at_sec, 3),
            "latencies": {
                "stt_latency_ms": round(self.stt_latency_ms, 2),
                "llm_latency_ms": round(self.llm_latency_ms, 2),
                "tts_latency_ms": round(self.tts_latency_ms, 2),
                "total_latency_ms": round(self.total_latency_ms, 2)
            },
            "memory_count": self.memory_count,
            "success": self.success,
            "error": self.error
        }


class VoiceOrchestrator:
    """
    Coordinates end-to-end voice interactions through Saki's existing brain.
    """

    def __init__(self):
        self._turn_lock = threading.Lock()
        self._is_session_active = False
        self._active_conversation_id: str = "voice-session"
        self._active_voice: str = "af_heart"
        self._total_voice_turns = 0
        self._voice_latencies: List[float] = []

    def interrupt_active_turn(
        self,
        conversation_id: str = "voice-session",
        reason: str = "manual_trigger"
    ) -> InterruptionRecord:
        """Explicitly cancels any active speech or playback for the conversation."""
        return interruption_controller.trigger_interruption(
            conversation_id=conversation_id,
            reason=reason,
            source="manual_trigger"
        )

    def execute_voice_turn(
        self,
        audio_input: Union[bytes, np.ndarray, SpeechSegment, str],
        conversation_id: str = "voice-session",
        voice: Optional[str] = None,
        speed: float = 1.0,
        play_locally: bool = False,
        request_id: Optional[str] = None
    ) -> VoiceTurnResult:
        """
        Executes a complete voice turn:
        1. Transcribes audio input via STT (Faster-Whisper).
        2. Routes transcript through existing Saki Brain (_execute_chat_pipeline + call_model).
        3. Synthesizes voice response via TTS (Kokoro).
        4. Optionally plays speech locally on host speakers.
        5. Returns structured VoiceTurnResult with full telemetry.
        """
        turn_t0 = time.perf_counter()
        req_id = request_id or f"vturn_{int(time.time() * 1000)}"
        voice_id = voice or self._active_voice or "af_heart"

        with self._turn_lock:
            # 0. Cancel any prior active playback before starting new voice turn
            tts_service.cancel_active_speech()

            # -------------------------------------------------------------
            # STEP 1: SPEECH-TO-TEXT (STT)
            # -------------------------------------------------------------
            if EVENTS_AVAILABLE and saki_event_manager is not None:
                try:
                    saki_event_manager.transition(
                        conversation_id=conversation_id,
                        request_id=req_id,
                        new_state=SakiState.PROCESSING,
                        activity="Transcribing user voice input...",
                        capability="SPEECH_TO_TEXT"
                    )
                except Exception:
                    pass

            from backend.services.resource_manager import resource_manager

            with resource_manager.acquire("stt_faster_whisper"):
                stt_res = stt_service.transcribe_speech(
                    audio_input=audio_input,
                    conversation_id=conversation_id,
                    request_id=req_id
                )

            stt_ms = stt_res.latency_ms
            transcript = stt_res.transcript.strip()

            # Handle empty transcript / unvoiced noise
            if not transcript:
                fallback_msg = "I didn't catch that. Could you please speak again?"
                tts_audio_bytes = None
                audio_dur_sec = 0.0
                b64_audio = None
                tts_prov = "kokoro"
                
                try:
                    with resource_manager.acquire("tts_kokoro"):
                        if play_locally:
                            tts_res = tts_service.synthesize_and_play(
                                text=fallback_msg,
                                voice=voice_id,
                                speed=speed,
                                conversation_id=conversation_id,
                                request_id=req_id,
                                language="en"
                            )
                        else:
                            tts_res = tts_service.synthesize_response(
                                text=fallback_msg,
                                voice=voice_id,
                                speed=speed,
                                conversation_id=conversation_id,
                                request_id=req_id,
                                language="en"
                            )
                        tts_audio_bytes = tts_res.audio_bytes
                        audio_dur_sec = tts_res.duration_seconds
                        tts_prov = tts_res.provider
                        if tts_audio_bytes:
                            b64_str = base64.b64encode(tts_audio_bytes).decode("utf-8")
                            b64_audio = f"data:audio/wav;base64,{b64_str}"
                except Exception:
                    pass

                total_ms = (time.perf_counter() - turn_t0) * 1000.0
                if EVENTS_AVAILABLE and saki_event_manager is not None:
                    try:
                        saki_event_manager.transition(
                            conversation_id=conversation_id,
                            request_id=req_id,
                            new_state=SakiState.IDLE,
                            activity="No speech detected in audio frame.",
                            capability="VOICE_PIPELINE"
                        )
                    except Exception:
                        pass

                return VoiceTurnResult(
                    transcript="",
                    response_text=fallback_msg,
                    conversation_id=conversation_id,
                    request_id=req_id,
                    audio_bytes=tts_audio_bytes,
                    audio_base64=b64_audio,
                    audio_duration_sec=audio_dur_sec,
                    voice_used=voice_id,
                    tts_provider=tts_prov,
                    stt_latency_ms=stt_ms,
                    total_latency_ms=total_ms,
                    success=True
                )

            # -------------------------------------------------------------
            # STEP 1.5: MULTILINGUAL SCRIPT & TRANSCRIPT CLASSIFICATION
            # -------------------------------------------------------------
            in_lang_profile = multilingual_service.classify_text(transcript)
            det_lang = in_lang_profile.language if in_lang_profile.language in ["te", "kn"] else (stt_res.language if stt_res.language in ["te", "kn"] else in_lang_profile.language)
            lang_confidence = in_lang_profile.confidence

            # -------------------------------------------------------------
            # STEP 2: SAKI BRAIN / CHAT PIPELINE EXECUTION (UNIFIED PIPELINE)
            # -------------------------------------------------------------
            t_llm_0 = time.perf_counter()
            from backend.services.brain_engine import brain_engine
            from brain.schemas import UnifiedTurnRequest, InputType

            unified_req = UnifiedTurnRequest(
                input_type=InputType.VOICE,
                text=transcript,
                conversation_id=conversation_id,
                turn_id=req_id,
                language_hint=det_lang,
                enable_tts=True,
                voice=voice_id,
                speed=speed,
                is_voice_mode=True,
                voice_metadata={
                    "stt_latency_ms": stt_ms,
                    "play_locally": play_locally
                }
            )

            try:
                chat_res = brain_engine.execute_turn(unified_req)
                final_text = chat_res.response
                selected_model = (chat_res.routing or {}).get("selected_model", "phi3:latest") if isinstance(chat_res.routing, dict) else getattr(chat_res.routing, "selected_model", "phi3:latest") if chat_res.routing else "phi3:latest"
                task_type = chat_res.intent or "casual_chat"
                conv_mode = chat_res.mode or "casual"
                b64_audio = chat_res.audio_base64
                tts_prov = (chat_res.tts_telemetry or {}).get("provider", "kokoro") if isinstance(chat_res.tts_telemetry, dict) else "kokoro"
                audio_dur_sec = (chat_res.tts_telemetry or {}).get("duration_seconds", 0.0) if isinstance(chat_res.tts_telemetry, dict) else 0.0
                effective_out_lang = chat_res.detected_language or det_lang
                tts_ms = (chat_res.tts_telemetry or {}).get("latency_ms", 0.0) if isinstance(chat_res.tts_telemetry, dict) else 0.0

                tts_audio_bytes = None
                if b64_audio:
                    try:
                        raw_b64 = b64_audio.split(",", 1)[1] if "," in b64_audio else b64_audio
                        tts_audio_bytes = base64.b64decode(raw_b64)
                    except Exception:
                        pass

                # If play_locally requested and we have audio, play it
                if play_locally and tts_audio_bytes:
                    try:
                        tts_service.playback_manager.play_wav_bytes_async(tts_audio_bytes)
                    except Exception:
                        pass
            except Exception as e:
                final_text = f"I encountered a temporary issue processing your query: {str(e)}"
                selected_model = "unknown"
                task_type = "error"
                conv_mode = "casual"
                effective_out_lang = det_lang
                tts_audio_bytes = None
                b64_audio = None
                audio_dur_sec = 0.0
                tts_prov = "kokoro"
                tts_ms = 0.0

            llm_ms = (time.perf_counter() - t_llm_0) * 1000.0
            total_ms = (time.perf_counter() - turn_t0) * 1000.0

            # -------------------------------------------------------------
            # STEP 4: TRANSITION TO IDLE (IF NOT PLAYING OR INTERRUPTED)
            # -------------------------------------------------------------
            if not play_locally and EVENTS_AVAILABLE and saki_event_manager is not None:
                try:
                    saki_event_manager.transition(
                        conversation_id=conversation_id,
                        request_id=req_id,
                        new_state=SakiState.IDLE,
                        activity="Voice turn complete. Ready for next turn.",
                        capability="VOICE_PIPELINE",
                        details={
                            "transcript": transcript,
                            "selected_model": selected_model,
                            "detected_language": det_lang,
                            "output_language": effective_out_lang,
                            "total_latency_ms": round(total_ms, 2)
                        }
                    )
                except Exception:
                    pass

            self._total_voice_turns += 1
            self._voice_latencies.append(total_ms)
            if len(self._voice_latencies) > 50:
                self._voice_latencies.pop(0)

            mem_data = load_memory()
            mem_count = len(mem_data.get("conversation_history", []))

            return VoiceTurnResult(
                transcript=transcript,
                response_text=final_text,
                conversation_id=conversation_id,
                request_id=req_id,
                selected_model=selected_model,
                task_type=task_type,
                conversation_mode=conv_mode,
                detected_language=det_lang,
                language_confidence=lang_confidence,
                output_language=effective_out_lang,
                language_profile=in_lang_profile.to_dict(),
                audio_bytes=tts_audio_bytes,
                audio_base64=b64_audio,
                audio_duration_sec=audio_dur_sec,
                voice_used=(chat_res.tts_telemetry or {}).get("voice", voice_id) if isinstance(chat_res.tts_telemetry, dict) else voice_id,
                tts_provider=tts_prov,
                stt_latency_ms=stt_ms,
                llm_latency_ms=llm_ms,
                tts_latency_ms=tts_ms,
                total_latency_ms=total_ms,
                memory_count=mem_count,
                interrupted=False,
                interrupted_at_sec=0.0,
                success=True
            )

    def start_voice_session(
        self,
        conversation_id: str = "voice-session",
        voice: str = "af_heart",
        device_index: Optional[int] = None
    ) -> bool:
        """Starts a live background microphone listening voice session with barge-in support."""
        with self._turn_lock:
            self._active_conversation_id = conversation_id
            self._active_voice = voice
            if device_index is not None:
                microphone_service.set_device(device_index)

            # Define speech callbacks with real-time barge-in interruption
            def handle_speech_start():
                if interruption_controller.is_saki_speaking(conversation_id):
                    interruption_controller.trigger_interruption(
                        conversation_id=conversation_id,
                        reason="user_speech_detected",
                        source="vad_speech_onset"
                    )

            def handle_speech_end(segment: SpeechSegment):
                # Run full voice turn in background worker thread
                threading.Thread(
                    target=self.execute_voice_turn,
                    args=(segment.audio_bytes, conversation_id, voice, 1.0, True),
                    daemon=True,
                    name="Saki-Voice-Turn-Worker"
                ).start()

            started = microphone_service.start_listening(
                on_speech_start=handle_speech_start,
                on_speech_end=handle_speech_end
            )
            self._is_session_active = started
            return started

    def stop_voice_session(self) -> bool:
        """Safely stops active voice session and halts audio capture and playback."""
        with self._turn_lock:
            microphone_service.stop_listening()
            tts_service.cancel_active_speech()
            self._is_session_active = False
            return True

    def get_status(self) -> Dict[str, Any]:
        """Gathers unified status across microphone, VAD, STT, LLM, TTS, and Interruption Controller."""
        mic_tel = microphone_service.get_telemetry()
        stt_tel = stt_service.get_telemetry()
        tts_stat = tts_service.get_status()
        intr_tel = interruption_controller.get_telemetry()

        avg_turn_lat = (
            sum(self._voice_latencies) / len(self._voice_latencies)
            if self._voice_latencies else 0.0
        )

        return {
            "is_session_active": self._is_session_active,
            "active_conversation_id": self._active_conversation_id,
            "active_voice": self._active_voice,
            "total_voice_turns": self._total_voice_turns,
            "avg_turn_latency_ms": round(avg_turn_lat, 2),
            "microphone": mic_tel.to_dict(),
            "stt": stt_tel.to_dict(),
            "tts": tts_stat,
            "interruption": intr_tel.to_dict()
        }


# Global Singleton Voice Orchestrator Instance
voice_orchestrator = VoiceOrchestrator()
