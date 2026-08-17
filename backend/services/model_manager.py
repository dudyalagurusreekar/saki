"""
Saki Model Manager & Performance Telemetry Service
Tracks real model state machine, manages Ollama keep_alive, records genuine execution
telemetry without fabrication, and provides system resource information.
"""

import time
import httpx
from typing import Dict, Any, List, Optional
from backend.core.config import settings

OLLAMA_BASE_URL = "http://localhost:11434"

# Model state machine states
STATE_OFF = "OFF"
STATE_LOADING = "LOADING"
STATE_ACTIVE = "ACTIVE"
STATE_IDLE = "IDLE"
STATE_UNLOADING = "UNLOADING"
STATE_ERROR = "ERROR"

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
    """

    def __init__(self):
        self._model_states: Dict[str, str] = {model: STATE_OFF for model in ALL_MODELS}
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
        if model in self._model_states:
            self._model_states[model] = state
        if state == STATE_ACTIVE:
            self._active_model = model

    def get_model_state(self, model: str) -> str:
        return self._model_states.get(model, STATE_OFF)

    def get_all_states(self) -> Dict[str, str]:
        return dict(self._model_states)

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
        Explicitly triggers Ollama keep_alive=0 to release VRAM/RAM.
        """
        self.set_model_state(model_name, STATE_UNLOADING)
        try:
            res = httpx.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": model_name, "keep_alive": 0},
                timeout=10.0
            )
            if res.status_code == 200:
                self.set_model_state(model_name, STATE_OFF)
                return True
            self.set_model_state(model_name, STATE_ERROR)
            return False
        except Exception as e:
            print(f"Error unloading model {model_name}: {e}")
            self.set_model_state(model_name, STATE_ERROR)
            return False

    def probe_ollama_status(self) -> Dict[str, Any]:
        """
        Probes real Ollama service for running models and overall connectivity.
        """
        try:
            # Check tags / available models
            tags_res = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
            if tags_res.status_code != 200:
                return {"connected": False, "loaded_models": [], "available_models": []}
            
            tags_data = tags_res.json()
            available = [m.get("name") for m in tags_data.get("models", [])]

            # Check currently running / loaded models
            loaded = []
            try:
                ps_res = httpx.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=3.0)
                if ps_res.status_code == 200:
                    ps_data = ps_res.json()
                    loaded = [m.get("name") for m in ps_data.get("models", [])]
            except Exception:
                pass

            # Sync internal state for loaded models
            for model in ALL_MODELS:
                if model in loaded:
                    if self._model_states[model] != STATE_ACTIVE:
                        self._model_states[model] = STATE_IDLE
                else:
                    if self._model_states[model] not in [STATE_LOADING, STATE_ACTIVE]:
                        self._model_states[model] = STATE_OFF

            return {
                "connected": True,
                "loaded_models": loaded,
                "available_models": available
            }
        except Exception:
            return {"connected": False, "loaded_models": [], "available_models": []}

    def get_system_resources(self) -> Dict[str, Any]:
        """
        Collects real system resource metrics if available, or returns Unavailable.
        """
        resources = {
            "gpu_name": "Unavailable",
            "vram_usage": "Unavailable",
            "ram_usage": "Unavailable",
            "loaded_models_count": len([s for s in self._model_states.values() if s in [STATE_ACTIVE, STATE_IDLE]])
        }

        try:
            import psutil
            mem = psutil.virtual_memory()
            resources["ram_usage"] = f"{round(mem.used / (1024**3), 1)}GB / {round(mem.total / (1024**3), 1)}GB ({mem.percent}%)"
        except ImportError:
            pass

        return resources


# Global model manager singleton
model_manager = ModelManager()
