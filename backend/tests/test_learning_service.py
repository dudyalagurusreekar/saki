import pytest
from backend.services.learning_service import detect_user_correction, apply_learned_policies
from backend.core.config import settings

def test_detect_user_routing_correction():
    correction = detect_user_correction("Don't route these questions to Hermes. Use Qwen3.")
    assert correction is not None
    assert correction["type"] == "ROUTING_OVERRIDE"
    assert "qwen3" in correction["content"].lower()

def test_detect_user_verbosity_preference():
    correction = detect_user_correction("Please keep your answers shorter and more concise")
    assert correction is not None
    assert correction["type"] == "STYLE_PREFERENCE"

def test_apply_learned_policies_overrides_model():
    mock_memory = {
        "memories": [
            {"type": "DECISION", "content": "Prefer Qwen3 over Hermes for complex questions"}
        ]
    }
    selected = apply_learned_policies(
        query="Why is this question complex?",
        default_model=settings.MODEL_HERMES,
        memory=mock_memory
    )
    assert selected == settings.MODEL_QWEN3
