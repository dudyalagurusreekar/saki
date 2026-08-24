"""
Unit tests for Saki Unified Event & State System (Sprint 1)
"""

import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.events import SakiState, SakiEventType, SakiEvent
from backend.services.event_system import event_manager, saki_state_scope
from backend.models.schemas import ChatRequest


client = TestClient(app)


def test_saki_state_enum():
    """Verify all 10 canonical Saki states exist."""
    expected_states = {
        "IDLE", "LISTENING", "PROCESSING", "THINKING", "SEARCHING",
        "VISION", "REMEMBERING", "ACTING", "SPEAKING", "ERROR"
    }
    actual_states = {s.value for s in SakiState}
    assert expected_states.issubset(actual_states)


def test_saki_event_model_and_sse():
    """Test SakiEvent model creation and SSE formatting."""
    event = SakiEvent(
        event_type=SakiEventType.STATE_CHANGE,
        conversation_id="test_conv_1",
        request_id="req_test_123",
        state=SakiState.PROCESSING,
        activity="Analyzing input query",
        task="coding",
        selected_model="qwen2.5-coder:7b",
        detected_language="en",
        memory_usage={"turns": 4},
        retrieval_status="IDLE",
        active_tool="CODE_EXEC",
        capability="DEVELOPMENT",
        latency_ms=12.5,
        details={"custom_key": "custom_val"}
    )

    data = event.to_dict()
    assert data["state"] == "PROCESSING"
    assert data["selected_model"] == "qwen2.5-coder:7b"
    assert data["active_tool"] == "CODE_EXEC"
    assert data["details"]["custom_key"] == "custom_val"

    sse_str = event.to_sse()
    assert sse_str.startswith("event: state_change\n")
    assert "data: " in sse_str
    assert sse_str.endswith("\n\n")


def test_event_manager_lifecycle_and_timing():
    """Test start_request, record_first_token, and transition metrics."""
    conv_id = "test_timing_conv"
    req_id = "req_timing_001"

    # Start request
    event_manager.start_request(conv_id, req_id)
    time.sleep(0.01)

    # Transition to PROCESSING
    evt_proc = event_manager.transition(
        conversation_id=conv_id,
        request_id=req_id,
        new_state=SakiState.PROCESSING,
        activity="Classifying intent"
    )
    assert evt_proc.state == SakiState.PROCESSING
    assert evt_proc.latency_ms is not None
    assert evt_proc.latency_ms > 0

    # Record first token
    ft_latency = event_manager.record_first_token(req_id)
    assert ft_latency is not None
    assert ft_latency > 0

    # Transition to SPEAKING
    evt_spk = event_manager.transition(
        conversation_id=conv_id,
        request_id=req_id,
        new_state=SakiState.SPEAKING,
        activity="Streaming response"
    )
    assert evt_spk.state == SakiState.SPEAKING
    assert evt_spk.first_token_latency_ms == ft_latency

    # Transition to IDLE
    evt_idle = event_manager.transition(
        conversation_id=conv_id,
        request_id=req_id,
        new_state=SakiState.IDLE,
        activity="Ready"
    )
    assert evt_idle.state == SakiState.IDLE
    assert event_manager.get_current_state(conv_id) == SakiState.IDLE


def test_sync_event_subscription():
    """Test pub/sub event broadcasting to synchronous subscribers."""
    conv_id = "test_sub_conv"
    req_id = "req_sub_001"
    q = event_manager.subscribe_sync(conv_id)

    try:
        event_manager.transition(
            conversation_id=conv_id,
            request_id=req_id,
            new_state=SakiState.SEARCHING,
            activity="Searching the web",
            active_tool="DUCKDUCKGO"
        )
        received_evt = q.get(timeout=2.0)
        assert received_evt.state == SakiState.SEARCHING
        assert received_evt.active_tool == "DUCKDUCKGO"
    finally:
        event_manager.unsubscribe_sync(q, conv_id)


def test_saki_state_scope_normal():
    """Test context manager under normal operation."""
    conv_id = "test_scope_normal"
    req_id = "req_scope_001"

    with saki_state_scope(conv_id, req_id, initial_state=SakiState.PROCESSING):
        assert event_manager.get_current_state(conv_id) == SakiState.PROCESSING
        event_manager.transition(conv_id, req_id, SakiState.THINKING)
        assert event_manager.get_current_state(conv_id) == SakiState.THINKING

    # After scope exit, state must automatically be IDLE
    assert event_manager.get_current_state(conv_id) == SakiState.IDLE


def test_saki_state_scope_error():
    """Test context manager catching unhandled exceptions."""
    conv_id = "test_scope_err"
    req_id = "req_scope_err_001"

    with pytest.raises(ValueError, match="Intentional failure"):
        with saki_state_scope(conv_id, req_id, initial_state=SakiState.PROCESSING):
            raise ValueError("Intentional failure")

    # After exception, state must reset to IDLE cleanly
    assert event_manager.get_current_state(conv_id) == SakiState.IDLE


def test_api_state_current_endpoint():
    """Test GET /api/state/current endpoint."""
    conv_id = "test_api_conv"
    event_manager.transition(
        conversation_id=conv_id,
        request_id="req_api_1",
        new_state=SakiState.IDLE,
        activity="System online and ready"
    )

    res = client.get(f"/api/state/current?conversation_id={conv_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "IDLE"
    assert data["conversation_id"] == conv_id
    assert "history" in data
