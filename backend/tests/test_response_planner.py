import pytest
from backend.core.saki_state import (
    SakiCognitiveState,
    ConversationState,
    UserCognitiveState,
    SakiInternalState,
    ContextState
)
from backend.services.response_planner import plan_response

def test_plan_response_for_frustrated_debugging():
    state = SakiCognitiveState(
        conversation=ConversationState(topic="Saki", mode="builder", task="bug_fixing", stage="debugging"),
        user_state=UserCognitiveState(emotion="frustrated", intensity=0.85, confidence=0.9, needs=["practical_help"]),
        saki_state=SakiInternalState(warmth=0.9, playfulness=0.3, seriousness=0.8, verbosity=0.6),
        context=ContextState(active_project="Saki", consecutive_frustrations=1)
    )
    plan = plan_response(state, query="FastAPI is throwing 500 internal server error again!")
    assert plan.goal == "isolate_bug_calmly_and_provide_fix"
    assert plan.tone == "calm_focused"
    assert plan.acknowledge_emotion is True
    assert plan.use_humor is False
    assert plan.technical_detail == "high"
    assert "isolate" in plan.directive_prompt.lower()

def test_plan_response_for_celebration():
    state = SakiCognitiveState(
        conversation=ConversationState(topic="Saki", mode="builder", task="code_implementation", stage="implementing"),
        user_state=UserCognitiveState(emotion="celebrating", intensity=0.9, confidence=0.9, needs=["celebration"]),
        saki_state=SakiInternalState(warmth=0.9, playfulness=0.9, seriousness=0.3, verbosity=0.4),
        context=ContextState(active_project="Saki")
    )
    plan = plan_response(state, query="It finally compiled and passed all tests!!")
    assert plan.goal == "celebrate_breakthrough_with_enthusiasm"
    assert plan.tone == "playful_banter"
    assert plan.use_humor is True

def test_plan_response_for_support_mode():
    state = SakiCognitiveState(
        conversation=ConversationState(topic="emotional_support", mode="support", task="emotional_venting", stage="exploring"),
        user_state=UserCognitiveState(emotion="sad", intensity=0.8, confidence=0.85, needs=["validation"]),
        saki_state=SakiInternalState(warmth=0.95, playfulness=0.1, seriousness=0.6, verbosity=0.5),
        context=ContextState()
    )
    plan = plan_response(state, query="I'm feeling really down and lonely today")
    assert plan.tone == "empathetic_gentle"
    assert plan.acknowledge_emotion is True
    assert plan.technical_detail == "none"
