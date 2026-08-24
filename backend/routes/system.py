import os
import json
import time
from fastapi import APIRouter, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.core.config import settings
from backend.services.model_manager import model_manager
from backend.services.resource_manager import resource_manager, ResourceState
from backend.services.memory_service import load_memory

router = APIRouter()

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "settings.json")


def load_persisted_settings() -> Dict[str, Any]:
    default_settings = {
        "theme": "clear_sky",
        "reduced_animation": False,
        "personality_warmth": 0.85,
        "personality_playfulness": 0.60,
        "personality_verbosity": 0.60,
        "privacy_mode": settings.PRIVACY_MODE,
        "auto_keep_alive": settings.MODEL_KEEP_ALIVE_SESSION
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings


def save_persisted_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    current = load_persisted_settings()
    current.update(new_settings)
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current


@router.get("/health")
def health():
    """
    Comprehensive health check probing backend, Ollama connectivity,
    loaded models, and durable memory store.
    """
    ollama_info = model_manager.probe_ollama_status()
    memory_ok = False
    try:
        mem = load_memory()
        memory_ok = bool(isinstance(mem, dict))
    except Exception:
        memory_ok = False

    overall_status = "Online"
    if not ollama_info["connected"]:
        overall_status = "Degraded" if memory_ok else "Offline"

    return {
        "status": overall_status,
        "backend": "ok",
        "ollama_connected": ollama_info["connected"],
        "loaded_models": ollama_info["loaded_models"],
        "available_models": ollama_info["available_models"],
        "memory_system": "ok" if memory_ok else "error"
    }


@router.get("/brain/status")
def get_brain_status():
    """
    Real-time performance, model state, resource, and cognitive telemetry.
    Never fabricates metrics.
    """
    telemetry = model_manager.get_latest_telemetry()
    resources = model_manager.get_system_resources()
    resource_matrix = resource_manager.get_resource_matrix()
    memory = load_memory()
    awareness = memory.get("awareness", {})
    cognitive = memory.get("cognitive_state", {})

    return {
        "model": telemetry.get("model", settings.MODEL_DEFAULT),
        "mode": awareness.get("conversation_mode", "casual"),
        "state": model_manager.get_model_state(telemetry.get("model", settings.MODEL_DEFAULT)),
        "latency_ms": telemetry.get("latency_ms", 0),
        "first_token_latency": telemetry.get("first_token_latency", 0.0),
        "tokens_per_second": telemetry.get("tokens_per_second", 0.0),
        "input_tokens": telemetry.get("input_tokens", 0),
        "output_tokens": telemetry.get("output_tokens", 0),
        "total_tokens": telemetry.get("total_tokens", 0),
        "memory_count": len(memory.get("memories", [])),
        "rag_enabled": telemetry.get("rag_enabled", False),
        "gpu_name": resources.get("gpu_name", "Unavailable"),
        "vram_usage": resources.get("vram_usage", "Unavailable"),
        "ram_usage": resources.get("ram_usage", "Unavailable"),
        "cpu_percent": resources.get("cpu_percent", 0.0),
        "loaded_models_count": resources.get("loaded_models_count", 0),
        "active_components": resource_matrix.get("active_components", []),
        "awareness": awareness,
        "cognitive_state": cognitive
    }


@router.get("/system/resources")
def get_system_resources_endpoint():
    """
    Returns complete real-time capability matrix, hardware telemetry,
    resident models, and active workloads.
    """
    return resource_manager.get_resource_matrix()


@router.post("/system/resources/unload")
def unload_resource_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Safely unloads an idle model or component from memory.
    """
    model_name = payload.get("model_name") or payload.get("component_id")
    if not model_name:
        return {"success": False, "error": "model_name or component_id is required"}

    force = payload.get("force", False)
    success = resource_manager.unload_model(model_name, force=force)
    return {
        "success": success,
        "component_id": model_name,
        "state": resource_manager.get_component_state(model_name).value
    }


@router.post("/system/resources/policy")
def update_resource_policy_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Updates keep-alive, low-memory thresholds, and auto-eviction policy.
    """
    if "keep_alive_seconds" in payload:
        resource_manager.keep_alive_seconds = float(payload["keep_alive_seconds"])
    if "low_memory_threshold_percent" in payload:
        resource_manager.low_memory_threshold_percent = float(payload["low_memory_threshold_percent"])
    if "auto_evict_enabled" in payload:
        resource_manager.auto_evict_enabled = bool(payload["auto_evict_enabled"])

    return {
        "success": True,
        "policies": {
            "keep_alive_seconds": resource_manager.keep_alive_seconds,
            "low_memory_threshold_percent": resource_manager.low_memory_threshold_percent,
            "auto_evict_enabled": resource_manager.auto_evict_enabled
        }
    }


@router.get("/config")
def get_config():
    return {
        "privacy_mode": settings.PRIVACY_MODE,
        "model_phi3": settings.MODEL_PHI3,
        "model_hermes": settings.MODEL_HERMES,
        "model_qwen3": settings.MODEL_QWEN3,
        "model_coder": settings.MODEL_CODER,
        "model_gemma": settings.MODEL_GEMMA,
        "model_default": settings.MODEL_DEFAULT,
        "max_memory": settings.MAX_MEMORY
    }


@router.get("/settings")
def get_settings():
    return load_persisted_settings()


@router.post("/settings")
def update_settings(payload: Dict[str, Any] = Body(...)):
    return save_persisted_settings(payload)


@router.get("/time")
def get_server_time():
    """
    Real-time clock endpoint providing rich temporal context.
    Returns current time, time-of-day classification, greeting,
    and human-readable descriptions for frontend display.
    """
    from backend.services.temporal_service import TemporalService
    return TemporalService.get_api_response()


# -------------------------
# SAKI EVENT & STATE ENDPOINTS
# -------------------------
from fastapi.responses import StreamingResponse
from backend.services.event_system import event_manager
from backend.models.schemas import SakiStateSnapshotSchema, SakiEventSchema


@router.get("/state/current", response_model=SakiStateSnapshotSchema)
def get_current_state(conversation_id: str = "default-session"):
    """
    Returns the real-time authoritative state and recent transition history for a conversation.
    """
    current_state = event_manager.get_current_state(conversation_id)
    history = event_manager.get_event_history(conversation_id)
    latest_event = history[-1] if history else None

    return SakiStateSnapshotSchema(
        state=current_state.value if hasattr(current_state, "value") else str(current_state),
        conversation_id=conversation_id,
        selected_model=latest_event.selected_model if latest_event else None,
        activity=latest_event.activity if latest_event else "Ready",
        task=latest_event.task if latest_event else "casual_chat",
        detected_language=latest_event.detected_language if latest_event else "en",
        timestamp=latest_event.timestamp if latest_event else time.time(),
        history=[SakiEventSchema(**e.model_dump()) for e in history]
    )


@router.get("/state/stream")
def state_stream(conversation_id: Optional[str] = None):
    """
    Global or conversation-scoped Server-Sent Events (SSE) stream
    broadcasting live Saki state changes to UI HUDs, telemetry panels, and background watchers.
    """
    import time
    q = event_manager.subscribe_sync(conversation_id)

    def event_generator():
        try:
            # Yield initial snapshot event
            initial_state = event_manager.get_current_state(conversation_id or "default-session")
            init_event = event_manager.transition(
                conversation_id=conversation_id or "default-session",
                request_id="sys_probe",
                new_state=initial_state,
                activity="SSE listener connected"
            )
            yield init_event.to_sse()

            while True:
                try:
                    # Wait up to 15s for next event or send heartbeat comment
                    evt = q.get(timeout=15.0)
                    yield evt.to_sse()
                except Exception:
                    # Send SSE heartbeat keep-alive
                    yield f": heartbeat {time.time()}\n\n"
        finally:
            event_manager.unsubscribe_sync(q, conversation_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")