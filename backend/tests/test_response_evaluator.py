import pytest
from backend.services.response_evaluator import evaluate_response, clean_speaker_tags
from backend.services.response_planner import ResponsePlan

def test_clean_speaker_tags():
    assert clean_speaker_tags("Saki: Hello there!") == "Hello there!"
    assert clean_speaker_tags("Assistant: How can I help?") == "How can I help?"
    assert clean_speaker_tags("AI - Ready to build.") == "Ready to build."

def test_evaluate_response_catches_and_cleanses_cliches():
    draft = "Hello! How can I assist you today? As an AI language model, I recommend checking your route handler."
    plan = ResponsePlan(goal="fix_bug", tone="calm_focused")
    result = evaluate_response(draft, plan=plan, mode="builder")
    assert result.passed is True
    assert "assist you today" not in result.repaired_text.lower()
    assert "as an ai" not in result.repaired_text.lower()
    assert len(result.persona_issues) > 0

def test_evaluate_response_clean_output():
    draft = "Ahh, that bug again 😭. Let's isolate the router traceback and check line 42."
    plan = ResponsePlan(goal="fix_bug", tone="calm_focused")
    result = evaluate_response(draft, plan=plan, mode="builder")
    assert result.passed is True
    assert result.score >= 0.9
    assert len(result.persona_issues) == 0
    assert "isolate the router traceback" in result.repaired_text


def test_evaluate_response_sanitizes_internal_leaks():
    draft = """[Instruction]
Respond with warmth.
Emotional Context: user is tired
Detected Emotion: fatigue
Durable Memory: knows user loves fast APIs
According to my instructions, I should help you.

Hey, you've been working hard today! Take a quick breath and let's check this."""
    result = evaluate_response(draft, mode="support")
    assert result.passed is True
    assert "[Instruction]" not in result.repaired_text
    assert "Emotional Context" not in result.repaired_text
    assert "Detected Emotion" not in result.repaired_text
    assert "Durable Memory" not in result.repaired_text
    assert "According to my instructions" not in result.repaired_text
    assert "working hard today" in result.repaired_text

