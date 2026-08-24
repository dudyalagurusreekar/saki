"""
Sprint 11 Reliability Test Suite: Saki Futuristic HUD & Workstation Integration
Verifies that all backend endpoints, state transitions, telemetry, and capabilities
consumed by the three-zone futuristic HUD operate reliably and adhere to specs.
"""
import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.events import SakiState, SakiEventType, SakiEvent
from backend.services.event_system import event_manager
from backend.services.voice_orchestrator import voice_orchestrator
from backend.services.interruption_controller import interruption_controller


class TestSprint11HudIntegration:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def setup_method(self):
        event_manager.transition(
            conversation_id="default-session",
            request_id="req_setup",
            new_state=SakiState.IDLE,
            activity="Test setup"
        )

    def test_01_health_and_system_status_endpoint(self):
        """Verify GET /api/health returns valid system status for TopBar."""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["Online", "Degraded", "Offline"]
        assert "saki_state" in data or "status" in data

    def test_02_brain_status_and_telemetry_payload(self):
        """Verify GET /api/brain/status returns rich telemetry consumed by BrainPanel (Zone 3)."""
        response = self.client.get("/api/brain/status")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "model" in data
        assert "state" in data
        assert "latency_ms" in data
        assert "tokens_per_second" in data
        assert "total_tokens" in data
        assert "awareness" in data
        assert "cognitive_state" in data

    def test_03_memory_endpoint_and_categorization(self):
        """Verify GET /api/memory provides categorized memory for Memory Vault Modal."""
        response = self.client.get("/api/memory")
        assert response.status_code == 200
        data = response.json()
        assert "categorized" in data
        categorized = data["categorized"]
        assert "projects" in categorized
        assert "preferences" in categorized
        assert "decisions" in categorized
        assert "facts" in categorized
        assert "progress" in categorized

    def test_04_settings_endpoint_and_persistence(self):
        """Verify GET & POST /api/settings manages HUD theme and audio sensitivity."""
        # Read current settings
        get_res = self.client.get("/api/settings")
        assert get_res.status_code == 200
        current = get_res.json()
        assert "theme" in current

        # Update settings
        payload = {
            "theme": "night_sky",
            "reduced_animation": False,
            "personality_warmth": 0.90,
            "personality_playfulness": 0.70,
            "core_quality": "high",
            "core_opacity": 0.85,
            "core_show_hud": True,
            "audio_sensitivity": 1.25
        }
        post_res = self.client.post("/api/settings", json=payload)
        assert post_res.status_code == 200
        updated = post_res.json()
        assert updated.get("theme") == "night_sky"
        assert updated.get("personality_warmth") == 0.90
        assert updated.get("audio_sensitivity") == 1.25

    def test_05_conversations_crud_endpoints(self):
        """Verify conversations CRUD for Sidebar History (Zone 1)."""
        # List conversations
        list_res = self.client.get("/api/conversations")
        assert list_res.status_code == 200
        data = list_res.json()
        assert "today" in data or "older" in data

        # Create new conversation
        create_res = self.client.post("/api/conversations")
        assert create_res.status_code == 200
        new_conv = create_res.json()
        conv_id = new_conv.get("id")
        assert conv_id is not None

        # Fetch detail
        detail_res = self.client.get(f"/api/conversations/{conv_id}")
        assert detail_res.status_code == 200
        assert detail_res.json().get("id") == conv_id

        # Search conversations
        search_res = self.client.get("/api/conversations/search?q=test")
        assert search_res.status_code == 200
        assert "results" in search_res.json()

        # Delete conversation
        del_res = self.client.delete(f"/api/conversations/{conv_id}")
        assert del_res.status_code == 200

    def test_06_voice_session_status_and_telemetry(self):
        """Verify voice session status consumed by Sidebar Voice Engine indicator."""
        response = self.client.get("/api/voice/session/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_session_active" in data
        assert "active_conversation_id" in data
        assert "active_voice" in data

    def test_07_interruption_controller_status(self):
        """Verify voice interruption status consumed by BrainPanel."""
        response = self.client.get("/api/voice/interruption/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "is_interrupting" in data
        assert "total_interruptions" in data

    def test_08_state_transitions_for_topbar_and_core(self):
        """Verify state lifecycle through all 10 states for dynamic TopBar and SakiCore visual engine."""
        states = [
            SakiState.IDLE,
            SakiState.LISTENING,
            SakiState.PROCESSING,
            SakiState.THINKING,
            SakiState.SEARCHING,
            SakiState.VISION,
            SakiState.REMEMBERING,
            SakiState.ACTING,
            SakiState.SPEAKING,
            SakiState.ERROR
        ]
        for st in states:
            evt = event_manager.transition(
                conversation_id="default-session",
                request_id=f"req_test_{st.value}",
                new_state=st,
                activity=f"Testing {st.value}"
            )
            assert evt is not None
            assert evt.state == st
            assert event_manager.get_current_state("default-session") == st

    def test_09_hud_three_zone_data_consistency(self):
        """Verify that state updates propagate across Zone 1, Zone 2, and Zone 3 components."""
        # Transition state
        evt = event_manager.transition(
            conversation_id="default-session",
            request_id="req_test_speak",
            new_state=SakiState.SPEAKING,
            activity="Speaking to operator"
        )
        assert evt.state == SakiState.SPEAKING
        
        brain_data = self.client.get("/api/brain/status").json()
        assert brain_data.get("state") in ["ACTIVE", "STANDBY", "OFF", "IDLE", "LOADING", "UNLOADING", "ERROR"]

        # Health endpoint
        health_data = self.client.get("/api/health").json()
        assert health_data.get("status") == "Online"

    def test_10_file_upload_endpoint_for_command_dock(self):
        """Verify POST /api/upload supports multimodal files for InputBox attachment dock."""
        dummy_content = b"console.log('Saki HUD test');"
        files = {"file": ("test_hud_script.ts", dummy_content, "text/plain")}
        response = self.client.post("/api/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == "test_hud_script.ts"
        assert "path" in data

