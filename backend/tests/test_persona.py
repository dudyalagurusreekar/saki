import pytest
from backend.core.saki_persona import (
    GLOBAL_SAKI_IDENTITY,
    CONVERSATIONAL_MODES,
    format_social_energy,
    format_conversational_habits,
    build_saki_system_prompt
)

def test_global_saki_identity_contains_core_traits():
    assert "You are Saki." in GLOBAL_SAKI_IDENTITY
    assert "Anti-Assistant Rules" in GLOBAL_SAKI_IDENTITY
    assert "How can I assist you today?" in GLOBAL_SAKI_IDENTITY
    assert "Healthy Boundaries" in GLOBAL_SAKI_IDENTITY

def test_all_five_modes_defined():
    expected_modes = ["casual", "support", "thinking", "builder", "vision"]
    for mode in expected_modes:
        assert mode in CONVERSATIONAL_MODES
        assert "title" in CONVERSATIONAL_MODES[mode]
        assert "directive" in CONVERSATIONAL_MODES[mode]

def test_social_energy_modulation():
    high_warmth = format_social_energy(energy=0.7, warmth=0.9, playfulness=0.5, seriousness=0.4)
    assert "warmth" in high_warmth.lower()

    high_playfulness = format_social_energy(energy=0.9, warmth=0.8, playfulness=0.8, seriousness=0.2)
    assert "playful" in high_playfulness.lower() or "humor" in high_playfulness.lower()

def test_conversational_habits_continuity():
    habits = format_conversational_habits(
        consecutive_frustrations=2,
        is_breakthrough=False,
        active_project="Saki"
    )
    assert "Saki" in habits
    assert "roadblocks" in habits.lower() or "calm" in habits.lower()

def test_conversational_habits_breakthrough():
    habits = format_conversational_habits(
        consecutive_frustrations=0,
        is_breakthrough=True,
        active_project="Saki"
    )
    assert "breakthrough" in habits.lower() or "celebrate" in habits.lower()

def test_build_saki_system_prompt():
    prompt = build_saki_system_prompt(
        mode="builder",
        energy=0.8,
        warmth=0.85,
        playfulness=0.5,
        seriousness=0.75,
        active_project="Saki",
        memory_context="- [PROJECT] User is building Saki",
        history_context="Recent Conversation:\n- User: hi\n- Saki: hey!"
    )
    assert "You are Saki." in prompt
    assert "Builder Mode" in prompt
    assert "What You Know" in prompt
    assert "Recent Conversation" in prompt
