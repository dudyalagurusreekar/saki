"""
FastAPI Routes for Saki Microphone & Voice Activity Detection (Sprint 6)

Provides endpoints for:
- Microphone hardware status & device enumeration
- Device selection & permission inspection
- Starting/stopping real-time background microphone capture
- Offline audio buffer VAD analysis (detect speech start/end in audio)
- Retrieving latest isolated user speech segment for Sprint 7 STT
"""

import io
import time
import base64
import soundfile as sf
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Response, status

from backend.services.microphone_service import (
    microphone_service,
    MicState,
    SpeechSegment,
    float32_to_wav_bytes
)
from backend.models.schemas import (
    MicDeviceSchema,
    MicStatusResponseSchema,
    MicStartRequestSchema,
    MicDeviceSelectSchema,
    VADProcessRequestSchema,
    VADProcessResponseSchema,
    SpeechSegmentMetadataSchema
)

router = APIRouter(prefix="/api/mic", tags=["Microphone & VAD"])


@router.get("/status", response_model=MicStatusResponseSchema)
def get_mic_status():
    """Returns the current state and telemetry of the microphone subsystem."""
    tel = microphone_service.get_telemetry()
    return MicStatusResponseSchema(
        state=tel.state,
        is_capturing=tel.is_capturing,
        speech_detected=tel.speech_detected,
        active_device_index=tel.device_index,
        active_device_name=tel.device_name,
        sample_rate=tel.sample_rate,
        vad_model=tel.vad_model,
        vad_available=microphone_service.vad.is_available(),
        init_time_ms=tel.init_time_ms,
        avg_chunk_latency_ms=tel.avg_chunk_latency_ms,
        cpu_percent=tel.cpu_percent,
        memory_mb=tel.memory_mb,
        total_speech_segments=tel.total_speech_segments,
        last_segment_duration_sec=tel.last_segment_duration_sec,
        error=tel.error
    )


@router.get("/devices", response_model=List[MicDeviceSchema])
def get_input_devices():
    """Lists all available audio input devices detected on the host system."""
    devs = microphone_service.list_devices()
    return [
        MicDeviceSchema(
            id=d["id"],
            name=d["name"],
            channels=d["channels"],
            default_samplerate=d["default_samplerate"],
            is_default=d.get("is_default", False)
        )
        for d in devs
    ]


@router.post("/device")
def select_input_device(req: MicDeviceSelectSchema):
    """Sets the active microphone input device."""
    ok = microphone_service.set_device(req.device_index)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change microphone input device while capture is actively running."
        )
    return {
        "status": "SUCCESS",
        "selected_device_index": req.device_index,
        "selected_device_name": microphone_service._selected_device_name
    }


@router.post("/start")
def start_mic(req: Optional[MicStartRequestSchema] = None):
    """Starts real-time non-blocking microphone capture and VAD detection."""
    device_idx = req.device_index if req else None
    timeout_sec = req.timeout_seconds if req else None
    threshold = req.threshold if req else 0.5
    min_silence = req.min_silence_duration_ms if req else 500

    if device_idx is not None:
        microphone_service.set_device(device_idx)

    microphone_service.vad.threshold = threshold
    microphone_service.vad.min_silence_duration_ms = min_silence

    ok = microphone_service.start_listening(timeout_seconds=timeout_sec)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=microphone_service.last_error or "Failed to start microphone listening."
        )

    tel = microphone_service.get_telemetry()
    return {
        "status": "LISTENING",
        "device_name": tel.device_name,
        "device_index": tel.device_index,
        "sample_rate": tel.sample_rate,
        "threshold": threshold,
        "min_silence_duration_ms": min_silence
    }


@router.post("/stop")
def stop_mic():
    """Stops microphone capture and releases hardware resources."""
    microphone_service.stop_listening()
    return {
        "status": "STOPPED",
        "state": microphone_service.current_state.value
    }


@router.post("/vad/process", response_model=VADProcessResponseSchema)
def process_audio_vad(req: VADProcessRequestSchema):
    """
    Offline/Direct VAD processing endpoint.
    Accepts Base64 audio (WAV/PCM), runs Silero VAD chunk-by-chunk,
    and returns speech detection intervals and metrics.
    """
    t0 = time.perf_counter()
    try:
        audio_raw_bytes = base64.b64decode(req.audio_base64)
        audio_data, sr = sf.read(io.BytesIO(audio_raw_bytes), dtype="float32")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio format or Base64 data: {str(e)}"
        )

    # Convert stereo to mono if necessary
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    # Resample to 16kHz if needed
    if sr != 16000:
        target_len = int(len(audio_data) * 16000 / float(sr))
        audio_16k = np.interp(
            np.linspace(0, len(audio_data), target_len, endpoint=False),
            np.arange(len(audio_data)),
            audio_data
        ).astype(np.float32)
    else:
        audio_16k = audio_data

    total_dur_sec = len(audio_16k) / 16000.0

    # Ensure VAD initialized
    if not microphone_service.vad.is_available():
        microphone_service.vad.initialize()

    microphone_service.vad.reset_state()
    chunk_size = 512
    detected_chunks = 0
    total_chunks = 0
    probs = []
    events = []

    for i in range(0, len(audio_16k), chunk_size):
        chunk = audio_16k[i:i+chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        total_chunks += 1
        prob, vad_ev = microphone_service.vad.process_chunk(chunk)
        probs.append(prob)
        if prob >= req.threshold:
            detected_chunks += 1
        if vad_ev:
            events.append({
                "timestamp_sec": round(i / 16000.0, 3),
                "event": vad_ev
            })

    speech_dur_sec = (detected_chunks * chunk_size) / 16000.0
    mean_prob = float(np.mean(probs)) if probs else 0.0
    speech_detected = detected_chunks > 0 or len(events) > 0
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Create segment metadata
    peak = float(np.max(np.abs(audio_16k))) if len(audio_16k) > 0 else 0.0
    rms = float(np.sqrt(np.mean(audio_16k ** 2))) if len(audio_16k) > 0 else 0.0

    seg_meta = SpeechSegmentMetadataSchema(
        sample_rate=16000,
        duration_seconds=round(total_dur_sec, 3),
        start_time=0.0,
        end_time=round(total_dur_sec, 3),
        sample_count=len(audio_16k),
        peak_amplitude=round(peak, 4),
        rms_energy=round(rms, 4),
        detection_latency_ms=round(elapsed_ms / max(1, total_chunks), 2),
        audio_size_bytes=len(audio_raw_bytes)
    )

    return VADProcessResponseSchema(
        speech_detected=speech_detected,
        speech_probability=round(mean_prob, 4),
        speech_duration_sec=round(speech_dur_sec, 3),
        total_duration_sec=round(total_dur_sec, 3),
        processing_time_ms=round(elapsed_ms, 2),
        speech_segments=events,
        segment_metadata=seg_meta
    )


@router.get("/latest-segment")
def get_latest_speech_segment():
    """
    Returns the latest user speech segment as a binary 16kHz WAV file.
    Includes speech duration and telemetry in HTTP headers.
    """
    segment = microphone_service.latest_speech_segment
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No speech segment has been captured yet."
        )

    headers = {
        "Content-Type": "audio/wav",
        "X-Speech-Duration-Sec": str(segment.duration_seconds),
        "X-Speech-Samples": str(segment.sample_count),
        "X-Speech-Peak": str(segment.peak_amplitude),
        "X-Speech-RMS": str(segment.rms_energy),
        "X-VAD-Latency-Ms": str(segment.detection_latency_ms),
        "X-Sample-Rate": "16000"
    }

    return Response(
        content=segment.audio_bytes,
        media_type="audio/wav",
        headers=headers
    )


@router.get("/latest-segment/json")
def get_latest_speech_segment_json():
    """
    Returns the latest user speech segment as JSON with Base64 audio + complete metadata.
    """
    segment = microphone_service.latest_speech_segment
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No speech segment has been captured yet."
        )

    b64_audio = base64.b64encode(segment.audio_bytes).decode("utf-8")
    return {
        "segment_metadata": segment.to_dict(),
        "audio_base64": b64_audio
    }
