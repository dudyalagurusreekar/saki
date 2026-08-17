import pytest
from backend.routes.system import (
    health,
    get_brain_status,
    get_config,
    get_settings,
    update_settings
)


def test_health_endpoint():
    res = health()
    assert "status" in res
    assert "backend" in res
    assert res["backend"] == "ok"
    assert "ollama_connected" in res
    assert "memory_system" in res


def test_brain_status_endpoint():
    status = get_brain_status()
    assert "model" in status
    assert "mode" in status
    assert "state" in status
    assert "latency_ms" in status
    assert "tokens_per_second" in status
    assert "memory_count" in status


def test_settings_endpoints():
    current = get_settings()
    assert "theme" in current

    updated = update_settings({"theme": "night_sky", "reduced_animation": True})
    assert updated["theme"] == "night_sky"
    assert updated["reduced_animation"] is True

    # Revert to clear_sky default
    reverted = update_settings({"theme": "clear_sky", "reduced_animation": False})
    assert reverted["theme"] == "clear_sky"


def test_config_endpoint():
    cfg = get_config()
    assert "privacy_mode" in cfg
    assert "model_phi3" in cfg
    assert "model_hermes" in cfg
    assert "model_qwen3" in cfg
    assert "model_coder" in cfg
    assert "model_gemma" in cfg
    assert "model_default" in cfg
    assert "max_memory" in cfg

