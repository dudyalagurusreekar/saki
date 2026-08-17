import pytest
from backend.services.emotional_intelligence import (
    analyze_emotional_state,
    calculate_social_energy,
    detect_activity,
    extract_active_project,
    build_awareness,
    EmotionalState
)

def test_analyze_frustration_emotion():
    state, frust_count = analyze_emotional_state("This stupid code is not working again! 😭", consecutive_frustrations=0)
    assert state.emotion == "frustrated"
    assert state.intensity >= 0.7
    assert frust_count == 1
    assert "acknowledgement" in state.needs or "practical_help" in state.needs

def test_analyze_celebrating_emotion():
    state, frust_count = analyze_emotional_state("YES! I finally fixed it and all tests passed!", consecutive_frustrations=2)
    assert state.emotion == "celebrating"
    assert state.intensity >= 0.8
    assert frust_count == 0  # reset on win
    assert "celebration" in state.needs

def test_analyze_loneliness_support_emotion():
    state, frust_count = analyze_emotional_state("I feel lonely and had a really rough day", consecutive_frustrations=0)
    assert state.emotion == "sad"
    assert state.intensity >= 0.7
    assert "warm_presence" in state.needs or "validation" in state.needs

def test_calculate_social_energy_frustrated():
    emo = EmotionalState(emotion="frustrated", intensity=0.85, needs=["practical_help"])
    energy = calculate_social_energy(emo, activity="coding", mode="builder")
    assert energy.warmth >= 0.85
    assert energy.seriousness >= 0.70
    assert energy.playfulness <= 0.50

def test_calculate_social_energy_celebrating():
    emo = EmotionalState(emotion="celebrating", intensity=0.90, needs=["celebration"])
    energy = calculate_social_energy(emo, activity="coding", mode="builder")
    assert energy.energy >= 0.90
    assert energy.playfulness >= 0.80

def test_extract_active_project():
    assert extract_active_project("Let's continue working on Saki architecture") == "Saki"
    assert extract_active_project("I am building Guardian AI for privacy") == "Guardian Ai"
    assert extract_active_project("Just random chat") == "Saki"

def test_build_awareness():
    awareness = build_awareness(
        query="Why is this FastAPI endpoint failing?",
        mode="builder",
        selected_model="qwen2.5-coder:7b",
        has_code=True
    )
    assert awareness.conversation_mode == "builder"
    assert awareness.current_activity == "coding"
    assert awareness.last_model == "qwen2.5-coder:7b"
