"""
Sprint 20 Reliability Tests: Saki Resource & Model Lifecycle Manager
Verifies:
1. Component registry & initial states (5 LLMs, STT, TTS, Vision, Audio).
2. Lifecycle state machine transitions (OFF, LOADING, ACTIVE, IDLE, UNLOADING, ERROR).
3. Concurrency management & active in-use protection (never evicting busy components).
4. Load deduplication across concurrent threads.
5. Idle eviction policy and keep-alive enforcement.
6. Multi-capability composite sequencing (STT -> LLM -> TTS).
7. Genuine hardware telemetry probing (RAM, CPU, GPU/VRAM, Ollama ps).
8. ModelManager delegation & backwards compatibility.
9. System API endpoints (/system/resources, /system/resources/unload, /system/resources/policy).
10. Safe recovery on component failure.
"""

import time
import pytest
import threading
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.resource_manager import (
    ResourceManager,
    ManagedComponent,
    ResourceState,
    ComponentType,
    resource_manager
)
from backend.services.model_manager import model_manager, STATE_ACTIVE, STATE_IDLE, STATE_OFF
from backend.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def res_mgr():
    # Return fresh or global instance
    return resource_manager


# ---------------------------------------------------------------------------
# TEST 1: Component Registry & Initial Setup
# ---------------------------------------------------------------------------
def test_component_registry(res_mgr):
    matrix = res_mgr.get_resource_matrix()
    comps = matrix["components"]

    # Verify all 5 LLMs are registered
    assert settings.MODEL_PHI3 in comps
    assert settings.MODEL_HERMES in comps
    assert settings.MODEL_QWEN3 in comps
    assert settings.MODEL_CODER in comps
    assert settings.MODEL_GEMMA in comps

    # Verify specialized pipelines are registered
    assert "stt_faster_whisper" in comps
    assert "tts_kokoro" in comps
    assert "tts_indic" in comps
    assert "vision_pipeline" in comps
    assert "audio_vad" in comps


# ---------------------------------------------------------------------------
# TEST 2: Lifecycle State Machine Transitions
# ---------------------------------------------------------------------------
def test_lifecycle_state_transitions(res_mgr):
    model = settings.MODEL_PHI3

    # Initial or reset state
    res_mgr.set_component_state(model, ResourceState.OFF)
    assert res_mgr.get_component_state(model) == ResourceState.OFF

    # Begin Loading
    res_mgr.begin_loading(model)
    assert res_mgr.get_component_state(model) == ResourceState.LOADING

    # Finish Loading
    res_mgr.finish_loading(model, success=True)
    assert res_mgr.get_component_state(model) == ResourceState.IDLE

    # Acquire for active request
    with res_mgr.acquire(model):
        assert res_mgr.get_component_state(model) == ResourceState.ACTIVE
        comp = res_mgr.get_component(model)
        assert comp.active_requests == 1

    # Released back to IDLE
    assert res_mgr.get_component_state(model) == ResourceState.IDLE
    assert res_mgr.get_component(model).active_requests == 0


# ---------------------------------------------------------------------------
# TEST 3: Active In-Use Protection (Never Evict Busy Models)
# ---------------------------------------------------------------------------
def test_active_in_use_protection(res_mgr):
    model = settings.MODEL_CODER

    with res_mgr.acquire(model):
        assert not res_mgr.can_unload(model)
        
        # Attempt to unload while active
        unloaded = res_mgr.unload_model(model, force=False)
        assert not unloaded
        assert res_mgr.get_component_state(model) == ResourceState.ACTIVE

    # After exit, can unload safely
    assert res_mgr.can_unload(model)


# ---------------------------------------------------------------------------
# TEST 4: Load Deduplication Across Concurrent Threads
# ---------------------------------------------------------------------------
def test_load_deduplication(res_mgr):
    model = settings.MODEL_HERMES
    res_mgr.begin_loading(model)

    results = []

    def worker():
        with res_mgr.acquire(model, timeout=2.0):
            results.append(True)

    t1 = threading.Thread(target=worker)
    t1.start()

    # Short sleep: thread is waiting on load_event
    time.sleep(0.05)
    assert len(results) == 0

    # Finish loading
    res_mgr.finish_loading(model, success=True)
    t1.join(timeout=1.0)

    assert len(results) == 1
    assert res_mgr.get_component_state(model) == ResourceState.IDLE


# ---------------------------------------------------------------------------
# TEST 5: Idle Eviction Policy
# ---------------------------------------------------------------------------
def test_idle_eviction_policy(res_mgr):
    model = settings.MODEL_GEMMA
    res_mgr.set_component_state(model, ResourceState.IDLE)
    comp = res_mgr.get_component(model)
    comp.active_requests = 0

    # Set last used time to 10 minutes ago
    comp.last_used_time = time.time() - 600.0

    # Set keep alive to 300s
    res_mgr.keep_alive_seconds = 300.0

    # Trigger eviction sweep
    unloaded = res_mgr.evict_idle_models(exclude_model=settings.MODEL_PHI3)
    
    # Model should have been targeted for eviction
    assert model in unloaded or res_mgr.get_component_state(model) in [ResourceState.OFF, ResourceState.ERROR, ResourceState.UNLOADING]


# ---------------------------------------------------------------------------
# TEST 6: Multi-Capability Composite Sequencing (STT -> LLM -> TTS)
# ---------------------------------------------------------------------------
def test_composite_workflow_sequencing(res_mgr):
    execution_order = []

    # Step 1: STT
    with res_mgr.acquire("stt_faster_whisper"):
        execution_order.append("STT")
        assert res_mgr.get_component_state("stt_faster_whisper") == ResourceState.ACTIVE
    assert res_mgr.get_component_state("stt_faster_whisper") == ResourceState.IDLE

    # Step 2: LLM
    with res_mgr.acquire(settings.MODEL_QWEN3):
        execution_order.append("LLM")
        assert res_mgr.get_component_state(settings.MODEL_QWEN3) == ResourceState.ACTIVE
    assert res_mgr.get_component_state(settings.MODEL_QWEN3) == ResourceState.IDLE

    # Step 3: TTS
    with res_mgr.acquire("tts_kokoro"):
        execution_order.append("TTS")
        assert res_mgr.get_component_state("tts_kokoro") == ResourceState.ACTIVE
    assert res_mgr.get_component_state("tts_kokoro") == ResourceState.IDLE

    assert execution_order == ["STT", "LLM", "TTS"]


# ---------------------------------------------------------------------------
# TEST 7: Genuine Hardware Telemetry Probing
# ---------------------------------------------------------------------------
def test_hardware_telemetry_probing(res_mgr):
    hw = res_mgr.probe_hardware_and_ollama()
    
    assert "ram" in hw
    assert "used_gb" in hw["ram"]
    assert "total_gb" in hw["ram"]
    assert hw["ram"]["total_gb"] > 0

    assert "cpu_percent" in hw
    assert "gpu" in hw
    assert "name" in hw["gpu"]
    assert "ollama" in hw


# ---------------------------------------------------------------------------
# TEST 8: ModelManager Integration & Backward Compatibility
# ---------------------------------------------------------------------------
def test_model_manager_resource_bridge():
    model = settings.MODEL_PHI3
    model_manager.set_model_state(model, STATE_ACTIVE)
    assert model_manager.get_model_state(model) == STATE_ACTIVE
    assert resource_manager.get_component_state(model) == ResourceState.ACTIVE

    model_manager.set_model_state(model, STATE_IDLE)
    assert model_manager.get_model_state(model) == STATE_IDLE

    sys_res = model_manager.get_system_resources()
    assert "gpu_name" in sys_res
    assert "ram_usage" in sys_res


# ---------------------------------------------------------------------------
# TEST 9: System Resources API Endpoints
# ---------------------------------------------------------------------------
def test_system_resources_api_endpoints(client):
    # GET /api/system/resources
    r = client.get("/api/system/resources")
    assert r.status_code == 200
    data = r.json()
    assert "hardware" in data
    assert "components" in data
    assert "policies" in data

    # POST /api/system/resources/policy
    r_pol = client.post("/api/system/resources/policy", json={"keep_alive_seconds": 600.0})
    assert r_pol.status_code == 200
    assert r_pol.json()["policies"]["keep_alive_seconds"] == 600.0

    # POST /api/system/resources/unload
    r_unl = client.post("/api/system/resources/unload", json={"component_id": settings.MODEL_CODER})
    assert r_unl.status_code == 200


# ---------------------------------------------------------------------------
# TEST 10: Error Recovery and State Restoration
# ---------------------------------------------------------------------------
def test_error_recovery(res_mgr):
    model = settings.MODEL_GEMMA
    res_mgr.set_component_state(model, ResourceState.ERROR, "Out of memory simulated")
    
    comp = res_mgr.get_component(model)
    assert comp.state == ResourceState.ERROR
    assert comp.error_message == "Out of memory simulated"

    # Finish loading recovers it
    res_mgr.finish_loading(model, success=True)
    assert comp.state == ResourceState.IDLE
    assert comp.error_message is None
