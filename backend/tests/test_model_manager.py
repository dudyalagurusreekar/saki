import pytest
from backend.services.model_manager import (
    ModelManager,
    STATE_OFF,
    STATE_LOADING,
    STATE_ACTIVE,
    STATE_IDLE,
    STATE_ERROR
)
from backend.core.config import settings


def test_model_manager_state_transitions():
    mgr = ModelManager()
    assert mgr.get_model_state(settings.MODEL_CODER) == STATE_OFF

    mgr.set_model_state(settings.MODEL_CODER, STATE_LOADING)
    assert mgr.get_model_state(settings.MODEL_CODER) == STATE_LOADING

    mgr.set_model_state(settings.MODEL_CODER, STATE_ACTIVE)
    assert mgr.get_model_state(settings.MODEL_CODER) == STATE_ACTIVE
    assert mgr.get_active_model() == settings.MODEL_CODER

    mgr.set_model_state(settings.MODEL_CODER, STATE_IDLE)
    assert mgr.get_model_state(settings.MODEL_CODER) == STATE_IDLE


def test_model_manager_telemetry_recording():
    mgr = ModelManager()
    mgr.record_telemetry(
        model=settings.MODEL_QWEN3,
        mode="thinking",
        latency_ms=1250.5,
        first_token_latency=0.45,
        tokens_per_second=32.4,
        input_tokens=150,
        output_tokens=75,
        memory_count=2,
        rag_enabled=False
    )
    tel = mgr.get_latest_telemetry()
    assert tel["model"] == settings.MODEL_QWEN3
    assert tel["mode"] == "thinking"
    assert tel["latency_ms"] == 1250.5
    assert tel["tokens_per_second"] == 32.4
    assert tel["total_tokens"] == 225
    assert tel["memory_count"] == 2


def test_model_manager_fallback():
    mgr = ModelManager()
    assert mgr.get_fallback_model(settings.MODEL_HERMES) == settings.MODEL_QWEN3
    assert mgr.get_fallback_model(settings.MODEL_CODER) == settings.MODEL_QWEN3
    assert mgr.get_fallback_model(settings.MODEL_GEMMA) == settings.MODEL_QWEN3
