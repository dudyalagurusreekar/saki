"""
Saki Voice & TTS API Endpoints (Sprint 4 & 5)
Exposes local Kokoro/Piper speech synthesis, non-blocking playback controls, voice selection,
and telemetry diagnostics.
"""

import base64
from fastapi import APIRouter, HTTPException, Response, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from backend.services.tts_service import tts_service, normalize_text_for_speech, KokoroTTSProvider
from backend.services.stt_service import stt_service
from backend.services.voice_orchestrator import voice_orchestrator
from backend.services.interruption_controller import interruption_controller
from backend.models.schemas import (
    STTTranscribeRequestSchema,
    STTTranscribeResponseSchema,
    STTTelemetrySchema,
    VoiceTurnRequestSchema,
    VoiceTurnLatenciesSchema,
    VoiceTurnResponseSchema,
    VoiceSessionStartRequestSchema,
    VoiceSessionStatusResponseSchema,
    VoiceInterruptRequestSchema,
    VoiceInterruptResponseSchema,
    InterruptionConfigSchema,
    InterruptionTelemetrySchema
)

router = APIRouter(tags=["voice"])


class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize into speech")
    voice: Optional[str] = Field("af_heart", description="Selected voice identifier (e.g. af_heart, af_bella)")
    speed: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speech rate multiplier")
    conversation_id: Optional[str] = Field("default-session", description="Associated conversation ID")


class VoiceSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    default_voice: Optional[str] = None
    default_speed: Optional[float] = None
    primary_provider: Optional[str] = None


@router.post("/voice/speak")
def speak(req: SpeakRequest):
    """
    Synthesizes text through the active local TTS provider and returns
    binary WAV audio with performance telemetry headers.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        result = tts_service.synthesize_response(
            text=req.text,
            voice=req.voice,
            speed=req.speed,
            conversation_id=req.conversation_id or "default-session"
        )

        headers = {
            "Content-Type": "audio/wav",
            "Content-Disposition": "inline; filename=saki_speech.wav",
            "X-TTS-Latency-Ms": str(round(result.latency_ms, 2)),
            "X-TTS-RTF": str(round(result.rtf, 3)),
            "X-TTS-Duration-Sec": str(round(result.duration_seconds, 3)),
            "X-TTS-Provider": result.provider,
            "X-TTS-Voice": result.voice,
            "X-TTS-Device": result.device,
            "X-TTS-Sample-Rate": str(result.sample_rate)
        }

        return Response(content=result.audio_bytes, media_type="audio/wav", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.post("/voice/synthesize")
def synthesize_json(req: SpeakRequest):
    """
    Synthesizes speech and returns Base64-encoded WAV with full telemetry payload in JSON format.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        result = tts_service.synthesize_response(
            text=req.text,
            voice=req.voice,
            speed=req.speed,
            conversation_id=req.conversation_id or "default-session"
        )

        b64_audio = base64.b64encode(result.audio_bytes).decode('utf-8')
        telemetry = result.to_dict()
        telemetry["audio_base64"] = f"data:audio/wav;base64,{b64_audio}"

        return telemetry
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.post("/voice/play")
def play_speech_locally(req: SpeakRequest):
    """
    Synthesizes text and plays audio locally on the host machine non-blockingly
    without creating temporary WAV files on disk.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        result = tts_service.synthesize_and_play(
            text=req.text,
            voice=req.voice,
            speed=req.speed,
            conversation_id=req.conversation_id or "default-session"
        )
        return {
            "status": "playing",
            "provider": result.provider,
            "voice": result.voice,
            "duration_seconds": round(result.duration_seconds, 3),
            "latency_ms": round(result.latency_ms, 2),
            "rtf": round(result.rtf, 3)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS playback failed: {str(e)}")


@router.post("/voice/stop")
def stop_speech():
    """Cancels any active in-progress speech generation and halts audio playback immediately."""
    tts_service.cancel_active_speech()
    return {"status": "stopped", "message": "Active speech generation and playback cancelled"}


@router.get("/voice/status")
def get_voice_status():
    """Returns runtime health, provider availability, model paths, and device configuration."""
    return tts_service.get_status()


@router.get("/voice/voices")
def get_available_voices():
    """Returns list of supported voices with persona descriptions and default recommendation."""
    active_prov = tts_service.get_active_provider()
    return {
        "active_provider": active_prov.get_status().get("provider", "unknown"),
        "voices": active_prov.get_voices(),
        "recommended_voice": "af_heart",
        "voice_personas": KokoroTTSProvider.VOICE_PERSONAS
    }


@router.post("/voice/settings")
def update_voice_settings(settings: VoiceSettingsUpdate):
    """Updates active voice preferences."""
    if settings.enabled is not None:
        tts_service.enabled = settings.enabled
    if settings.default_voice is not None:
        tts_service.default_voice = settings.default_voice
    if settings.default_speed is not None:
        tts_service.default_speed = settings.default_speed
    if settings.primary_provider is not None:
        tts_service.primary_provider = settings.primary_provider

    return tts_service.get_status()


# ---------------------------------------------------------
# SPRINT 8: SPEECH-TO-TEXT (STT) ENDPOINTS
# ---------------------------------------------------------
@router.post("/voice/transcribe", response_model=STTTranscribeResponseSchema)
def transcribe_audio(req: STTTranscribeRequestSchema):
    """
    Transcribes Base64-encoded audio (WAV/PCM/WebM) using local Faster-Whisper.
    """
    if not req.audio_base64 or not req.audio_base64.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audio_base64 cannot be empty."
        )

    b64_str = req.audio_base64.strip()
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(b64_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Base64 audio encoding: {str(e)}"
        )

    res = stt_service.transcribe_speech(
        audio_input=raw_bytes,
        language=req.language
    )

    if not res.success and res.error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res.error
        )

    return STTTranscribeResponseSchema(
        transcript=res.transcript,
        language=res.language,
        language_probability=res.language_probability,
        duration_seconds=res.duration_seconds,
        latency_ms=res.latency_ms,
        rtf=res.rtf,
        model_name=res.model_name,
        device=res.device,
        compute_type=res.compute_type,
        word_count=res.word_count,
        segments=res.segments,
        success=res.success,
        error=res.error
    )


@router.get("/voice/stt/status", response_model=STTTelemetrySchema)
def get_stt_status():
    """Returns runtime telemetry, model details, and performance metrics for STT."""
    tel = stt_service.get_telemetry()
    return STTTelemetrySchema(
        model_name=tel.model_name,
        is_loaded=tel.is_loaded,
        init_time_ms=tel.init_time_ms,
        device=tel.device,
        compute_type=tel.compute_type,
        total_transcriptions=tel.total_transcriptions,
        avg_latency_ms=tel.avg_latency_ms,
        avg_rtf=tel.avg_rtf,
        cpu_percent=tel.cpu_percent,
        memory_mb=tel.memory_mb,
        last_transcript=tel.last_transcript,
        last_error=tel.last_error
    )


# ---------------------------------------------------------
# SPRINT 8: UNIFIED VOICE TURN & SESSION ENDPOINTS
# ---------------------------------------------------------
@router.post("/voice/turn", response_model=VoiceTurnResponseSchema)
def execute_voice_turn(req: VoiceTurnRequestSchema):
    """
    Executes a complete end-to-end voice turn:
    Audio (Base64) -> Faster-Whisper STT -> Existing Saki Brain -> Kokoro TTS -> VoiceTurnResponse
    """
    if not req.audio_base64 or not req.audio_base64.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audio_base64 payload is required for voice turn execution."
        )

    b64_str = req.audio_base64.strip()
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(b64_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Base64 audio encoding: {str(e)}"
        )

    turn_res = voice_orchestrator.execute_voice_turn(
        audio_input=raw_bytes,
        conversation_id=req.conversation_id or "voice-session",
        voice=req.voice or "af_heart",
        speed=req.speed or 1.0,
        play_locally=req.play_locally
    )

    return VoiceTurnResponseSchema(
        transcript=turn_res.transcript,
        response_text=turn_res.response_text,
        conversation_id=turn_res.conversation_id,
        request_id=turn_res.request_id,
        selected_model=turn_res.selected_model,
        task_type=turn_res.task_type,
        conversation_mode=turn_res.conversation_mode,
        detected_language=turn_res.detected_language,
        language_confidence=turn_res.language_confidence,
        output_language=turn_res.output_language,
        language_profile=turn_res.language_profile,
        has_audio=turn_res.audio_bytes is not None and len(turn_res.audio_bytes) > 0,
        audio_base64=turn_res.audio_base64,
        audio_duration_sec=turn_res.audio_duration_sec,
        voice_used=turn_res.voice_used,
        tts_provider=turn_res.tts_provider,
        latencies=VoiceTurnLatenciesSchema(
            stt_latency_ms=turn_res.stt_latency_ms,
            llm_latency_ms=turn_res.llm_latency_ms,
            tts_latency_ms=turn_res.tts_latency_ms,
            total_latency_ms=turn_res.total_latency_ms
        ),
        memory_count=turn_res.memory_count,
        interrupted=turn_res.interrupted,
        interrupted_at_sec=turn_res.interrupted_at_sec,
        success=turn_res.success,
        error=turn_res.error
    )


@router.post("/voice/session/start")
def start_voice_session(req: Optional[VoiceSessionStartRequestSchema] = None):
    """
    Starts real-time continuous background voice listening loop on the local microphone.
    """
    conv_id = req.conversation_id if req else "voice-session"
    voice = req.voice if req else "af_heart"
    dev_idx = req.device_index if req else None

    ok = voice_orchestrator.start_voice_session(
        conversation_id=conv_id,
        voice=voice,
        device_index=dev_idx
    )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start background voice session on microphone."
        )

    return {
        "status": "LISTENING",
        "conversation_id": conv_id,
        "voice": voice,
        "message": "Continuous local voice listening active."
    }


@router.post("/voice/session/stop")
def stop_voice_session():
    """
    Halts active voice session, stops microphone capture, and cancels speech output.
    """
    voice_orchestrator.stop_voice_session()
    return {
        "status": "STOPPED",
        "message": "Voice session halted and resources released."
    }


@router.get("/voice/session/status", response_model=VoiceSessionStatusResponseSchema)
def get_voice_session_status():
    """
    Returns unified health and telemetry across microphone, VAD, STT, LLM, and TTS.
    """
    stat = voice_orchestrator.get_status()
    return VoiceSessionStatusResponseSchema(
        is_session_active=stat["is_session_active"],
        active_conversation_id=stat["active_conversation_id"],
        active_voice=stat["active_voice"],
        total_voice_turns=stat["total_voice_turns"],
        avg_turn_latency_ms=stat["avg_turn_latency_ms"],
        microphone=stat["microphone"],
        stt=stat["stt"],
        tts=stat["tts"],
        interruption=stat.get("interruption", {})
    )


# ---------------------------------------------------------
# SPRINT 9: VOICE INTERRUPTION / BARGE-IN ENDPOINTS
# ---------------------------------------------------------
@router.post("/voice/interrupt", response_model=VoiceInterruptResponseSchema)
def trigger_voice_interruption(req: Optional[VoiceInterruptRequestSchema] = None):
    """
    Explicitly triggers an interruption: halts active speech synthesis and in-memory playback (< 30ms)
    and transitions Saki to LISTENING state.
    """
    conv_id = req.conversation_id if req and req.conversation_id else "voice-session"
    reason = req.reason if req and req.reason else "manual_trigger"

    record = interruption_controller.trigger_interruption(
        conversation_id=conv_id,
        reason=reason,
        source="manual_api"
    )

    return VoiceInterruptResponseSchema(
        interruption_id=record.interruption_id,
        status="INTERRUPTED",
        reaction_latency_ms=record.reaction_latency_ms,
        message="Active speech generation and playback successfully cancelled.",
        conversation_id=conv_id
    )


@router.get("/voice/interruption/status", response_model=InterruptionTelemetrySchema)
def get_interruption_status():
    """
    Returns runtime telemetry and configuration for the interruption controller.
    """
    tel = interruption_controller.get_telemetry()
    return InterruptionTelemetrySchema(
        enabled=tel.enabled,
        is_interrupting=tel.is_interrupting,
        total_interruptions=tel.total_interruptions,
        avg_reaction_latency_ms=tel.avg_reaction_latency_ms,
        min_speech_duration_ms=tel.min_speech_duration_ms,
        min_consecutive_chunks=tel.min_consecutive_chunks,
        vad_threshold=tel.vad_threshold,
        last_interruption=tel.last_interruption
    )


@router.post("/voice/interruption/config", response_model=InterruptionTelemetrySchema)
def update_interruption_config(cfg: InterruptionConfigSchema):
    """
    Updates runtime debounce sensitivity and configuration for the interruption controller.
    """
    tel = interruption_controller.update_config(
        enabled=cfg.enabled,
        min_speech_duration_ms=cfg.min_speech_duration_ms,
        min_consecutive_chunks=cfg.min_consecutive_chunks,
        vad_threshold=cfg.vad_threshold
    )
    return InterruptionTelemetrySchema(
        enabled=tel.enabled,
        is_interrupting=tel.is_interrupting,
        total_interruptions=tel.total_interruptions,
        avg_reaction_latency_ms=tel.avg_reaction_latency_ms,
        min_speech_duration_ms=tel.min_speech_duration_ms,
        min_consecutive_chunks=tel.min_consecutive_chunks,
        vad_threshold=tel.vad_threshold,
        last_interruption=tel.last_interruption
    )

