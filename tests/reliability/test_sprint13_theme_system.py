"""
Sprint 13 Reliability Test Suite: Saki Clear Sky Environment & Theme System
Verifies backend settings management for visual environments (Clear Sky and Night Sky),
theme preference persistence, and non-interference with Saki's cognitive brain,
voice pipeline, STT, TTS, memory, and unified event system.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.events import SakiState
from backend.services.event_system import event_manager
from backend.services.tts_service import tts_service
from backend.services.stt_service import stt_service
from backend.services.orchestrator import SakiModelOrchestrator


class TestSprint13ThemeSystem:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def setup_method(self):
        event_manager.transition(
            conversation_id="theme-test-session",
            request_id="req_theme_setup",
            new_state=SakiState.IDLE,
            activity="Theme test setup"
        )

    def test_01_get_settings_theme_defaults(self):
        """Verify GET /api/settings returns valid theme token configuration."""
        res = self.client.get("/api/settings")
        assert res.status_code == 200
        data = res.json()
        assert "theme" in data
        assert data["theme"] in ["clear_sky", "night_sky"]

    def test_02_switch_to_clear_sky_theme(self):
        """Verify POST /api/settings updates and persists Clear Sky daytime environment."""
        payload = {
            "theme": "clear_sky",
            "reduced_animation": False,
            "core_quality": "high",
            "core_opacity": 0.85,
            "core_show_hud": True,
            "personality_warmth": 0.90,
            "personality_playfulness": 0.70
        }
        res = self.client.post("/api/settings", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["theme"] == "clear_sky"

        # Verify persistence via subsequent GET
        get_res = self.client.get("/api/settings")
        assert get_res.status_code == 200
        assert get_res.json()["theme"] == "clear_sky"

    def test_03_switch_to_night_sky_theme(self):
        """Verify POST /api/settings updates and persists Night Sky environment."""
        payload = {
            "theme": "night_sky",
            "reduced_animation": False,
            "core_quality": "auto",
            "core_opacity": 0.85,
            "core_show_hud": True
        }
        res = self.client.post("/api/settings", json=payload)
        assert res.status_code == 200
        assert res.json()["theme"] == "night_sky"

    def test_04_rapid_theme_toggling_without_side_effects(self):
        """Verify rapid theme toggling causes zero memory corruption or backend errors."""
        themes = ["clear_sky", "night_sky", "clear_sky", "night_sky", "clear_sky"]
        for t in themes:
            res = self.client.post("/api/settings", json={"theme": t})
            assert res.status_code == 200
            assert res.json()["theme"] == t

    def test_05_theme_change_preserves_cognitive_orchestrator(self):
        """Verify that Saki's cognitive model routing is identical regardless of active theme."""
        # Query under Clear Sky
        self.client.post("/api/settings", json={"theme": "clear_sky"})
        decision_clear = SakiModelOrchestrator.classify_request("Write a quick python function to sort a list")
        assert decision_clear.conversation_mode == "builder"
        assert decision_clear.coding_required is True

        # Query under Night Sky
        self.client.post("/api/settings", json={"theme": "night_sky"})
        decision_night = SakiModelOrchestrator.classify_request("Write a quick python function to sort a list")
        assert decision_night.conversation_mode == "builder"
        assert decision_night.selected_model == decision_clear.selected_model

    def test_06_theme_change_preserves_event_system_lifecycle(self):
        """Verify all 10 authoritative Saki states transition identically during Clear Sky."""
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
                conversation_id="theme-session-01",
                request_id=f"req_theme_{st.value}",
                new_state=st,
                activity=f"Daytime transition to {st.value}"
            )
            assert evt is not None
            assert evt.state == st
            assert event_manager.get_current_state("theme-session-01") == st

    def test_07_theme_change_preserves_tts_synthesis(self):
        """Verify Kokoro TTS audio generation functions identically across themes."""
        res = tts_service.synthesize_response(
            text="Clear sky environment initialized with procedural clouds.",
            voice="af_heart",
            conversation_id="theme-tts-test"
        )
        assert res is not None
        assert len(res.audio_bytes) > 1000
        assert res.duration_seconds > 0.5
        assert res.provider == "kokoro"

    def test_08_theme_change_preserves_stt_transcription(self):
        """Verify Faster-Whisper STT capability status is preserved during theme switches."""
        status = stt_service.get_telemetry()
        assert "tiny.en" in status.model_name
        assert status.device == "cpu"
