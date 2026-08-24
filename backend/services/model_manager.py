"""
Saki Model Manager & Performance Telemetry Service
Bridges model operations to the central ResourceManager (Sprint 20).
Tracks real model state machine, manages Ollama keep_alive, records genuine execution
telemetry without fabrication, and provides system resource information.
"""

import time
import httpx
from typing import Dict, Any, List, Optional
from backend.core.config import settings
from backend.services.resource_manager import (
    resource_manager,
    ResourceState,
    ComponentType,
    OLLAMA_BASE_URL
)

# Model state machine states (backwards-compatible constants)
STATE_OFF = ResourceState.OFF.value
STATE_LOADING = ResourceState.LOADING.value
STATE_ACTIVE = ResourceState.ACTIVE.value
STATE_IDLE = ResourceState.IDLE.value
STATE_UNLOADING = ResourceState.UNLOADING.value
STATE_ERROR = ResourceState.ERROR.value

ALL_MODELS = [
    settings.MODEL_PHI3,
    settings.MODEL_HERMES,
    settings.MODEL_QWEN3,
    settings.MODEL_CODER,
    settings.MODEL_GEMMA
]


class ModelManager:
    """
    Manages local LLM life cycle, state machine, and real runtime telemetry.
    Delegates lifecycle and hardware queries to central ResourceManager.
    """

    def __init__(self):
        self._active_model: str = settings.MODEL_DEFAULT
        self._current_mode: str = "casual"
        self._last_telemetry: Dict[str, Any] = {
            "model": settings.MODEL_DEFAULT,
            "mode": "casual",
            "state": STATE_OFF,
            "latency_ms": 0,
            "first_token_latency": 0.0,
            "tokens_per_second": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "memory_count": 0,
            "rag_enabled": False,
            "timestamp": time.time()
        }

    def set_model_state(self, model: str, state: str) -> None:
        try:
            rstate = ResourceState(state)
        except ValueError:
            rstate = ResourceState.OFF
        resource_manager.set_component_state(model, rstate)
        if state == STATE_ACTIVE:
            self._active_model = model

    def get_model_state(self, model: str) -> str:
        return resource_manager.get_component_state(model).value

    def get_all_states(self) -> Dict[str, str]:
        matrix = resource_manager.get_resource_matrix()
        return {k: v["state"] for k, v in matrix.get("components", {}).items() if k in ALL_MODELS}

    def get_active_model(self) -> str:
        return self._active_model

    def record_telemetry(
        self,
        model: str,
        mode: str,
        latency_ms: float,
        first_token_latency: float,
        tokens_per_second: float,
        input_tokens: int,
        output_tokens: int,
        memory_count: int = 0,
        rag_enabled: bool = False
    ) -> None:
        """Records genuine performance metrics after execution."""
        total_tokens = input_tokens + output_tokens
        self._last_telemetry = {
            "model": model,
            "mode": mode,
            "state": self.get_model_state(model),
            "latency_ms": round(latency_ms, 1),
            "first_token_latency": round(first_token_latency, 2),
            "tokens_per_second": round(tokens_per_second, 1),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "memory_count": memory_count,
            "rag_enabled": rag_enabled,
            "timestamp": time.time()
        }

    def get_latest_telemetry(self) -> Dict[str, Any]:
        return dict(self._last_telemetry)

    def get_fallback_model(self, failed_model: str) -> str:
        """
        Determines fallback model when a specialist model fails.
        """
        if failed_model == settings.MODEL_GEMMA:
            return settings.MODEL_QWEN3
        if failed_model in [settings.MODEL_HERMES, settings.MODEL_CODER, settings.MODEL_PHI3]:
            return settings.MODEL_QWEN3
        return settings.MODEL_DEFAULT

    def unload_model(self, model_name: str) -> bool:
        """
        Explicitly triggers Ollama keep_alive=0 via ResourceManager to release VRAM/RAM.
        """
        return resource_manager.unload_model(model_name)

    def probe_ollama_status(self) -> Dict[str, Any]:
        """
        Probes real Ollama service for running models and overall connectivity.
        """
        hw = resource_manager.probe_hardware_and_ollama()
        ollama_hw = hw.get("ollama", {})

        available = []
        try:
            tags_res = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
            if tags_res.status_code == 200:
                tags_data = tags_res.json()
                available = [m.get("name") for m in tags_data.get("models", [])]
        except Exception:
            pass

        return {
            "connected": ollama_hw.get("connected", False),
            "loaded_models": ollama_hw.get("loaded_models", []),
            "available_models": available,
            "total_vram_mb": ollama_hw.get("total_vram_mb", 0.0)
        }

    def get_system_resources(self) -> Dict[str, Any]:
        """
        Collects real system resource metrics if available, or returns Unavailable.
        """
        hw = resource_manager.probe_hardware_and_ollama()
        matrix = resource_manager.get_resource_matrix()

        return {
            "gpu_name": hw["gpu"]["name"],
            "vram_usage": hw["gpu"]["display"],
            "ram_usage": hw["ram"]["display"],
            "cpu_percent": hw["cpu_percent"],
            "loaded_models_count": matrix.get("loaded_components_count", 0)
        }


# Global model manager singleton
model_manager = ModelManager()

