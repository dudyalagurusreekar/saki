import pytest
from backend.services.orchestrator import SakiModelOrchestrator
from backend.core.config import settings

def test_greeting_routes_to_casual_phi3():
    decision = SakiModelOrchestrator.classify_request("hello Saki")
    assert decision.selected_model == settings.MODEL_PHI3
    assert decision.conversation_mode == "casual"
    assert decision.complexity == "low"
    assert decision.social_energy.playfulness >= 0.6

def test_emotional_support_routes_to_support_hermes():
    decision = SakiModelOrchestrator.classify_request("I had a terrible day and feel lonely")
    assert decision.selected_model == settings.MODEL_HERMES
    assert decision.conversation_mode == "support"
    assert decision.emotional_importance == "high"
    assert decision.task_type == "emotional_support"
    assert decision.social_energy.warmth >= 0.85

def test_coding_request_routes_to_builder_coder():
    decision = SakiModelOrchestrator.classify_request("Fix this Python code error: TypeError: 'int' object is not iterable")
    assert decision.selected_model == settings.MODEL_CODER
    assert decision.conversation_mode == "builder"
    assert decision.coding_required is True
    assert decision.task_type == "coding_task"
    assert decision.awareness.current_activity == "coding"

def test_conceptual_question_routes_to_thinking_qwen3():
    decision = SakiModelOrchestrator.classify_request("What is the difference between a process and a thread?")
    assert decision.selected_model == settings.MODEL_QWEN3
    assert decision.conversation_mode == "thinking"
    assert decision.coding_required is False

def test_vision_request_routes_to_vision_gemma():
    attachments = [{"name": "screenshot.png", "type": "image", "size": "2MB", "checksum": "12345"}]
    decision = SakiModelOrchestrator.classify_request("What is wrong with this screenshot?", attachments=attachments)
    assert decision.selected_model == settings.MODEL_GEMMA
    assert decision.conversation_mode == "vision"
    assert decision.vision_required is True

def test_frustrated_coding_routes_to_builder_with_frustration_state():
    decision = SakiModelOrchestrator.classify_request("I'm so frustrated! Why is my FastAPI endpoint failing with 500 internal server error?")
    assert decision.selected_model == settings.MODEL_CODER
    assert decision.conversation_mode == "builder"
    assert decision.coding_required is True
    assert decision.detected_emotion == "frustrated"
    assert decision.social_energy.warmth >= 0.85

def test_memory_inquiry_detects_memory_required():
    decision = SakiModelOrchestrator.classify_request("Do you remember what my project architecture is?")
    assert decision.memory_required is True
