import os
import json
from fastapi import APIRouter, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.core.config import settings
from backend.services.model_manager import model_manager
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
        "loaded_models_count": resources.get("loaded_models_count", 0),
        "awareness": awareness,
        "cognitive_state": cognitive
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