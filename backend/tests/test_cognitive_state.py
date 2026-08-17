import pytest
from backend.core.saki_state import (
    SakiCognitiveState,
    ConversationState,
    UserCognitiveState,
    SakiInternalState,
    ContextState,
    infer_task_and_stage
)

def test_infer_task_and_stage_bug_fixing():
    task, stage = infer_task_and_stage("My FastAPI endpoint is failing with 500 error", mode="builder", is_coding=True, has_image=False)
    assert task == "bug_fixing"
    assert stage == "debugging"

def test_infer_task_and_stage_architecture():
    task, stage = infer_task_and_stage("How should we plan the architecture of Saki?", mode="builder", is_coding=True, has_image=False)
    assert task == "architecture_design"
    assert stage == "planning"

def test_infer_task_and_stage_concept_learning():
    task, stage = infer_task_and_stage("What is the difference between a mutex and a semaphore?", mode="thinking", is_coding=False, has_image=False)
    assert task == "concept_learning"
    assert stage == "exploring"

def test_cognitive_state_serialization():
    state = SakiCognitiveState(
        conversation=ConversationState(topic="Saki", mode="builder", task="bug_fixing", stage="debugging"),
        user_state=UserCognitiveState(emotion="frustrated", intensity=0.8, confidence=0.9, needs=["practical_help"]),
        saki_state=SakiInternalState(warmth=0.9, playfulness=0.3, seriousness=0.8, verbosity=0.6),
        context=ContextState(active_project="Saki", last_model="qwen2.5-coder:7b", recent_topic="bug_fixing")
    )
    d = state.model_dump()
    assert d["conversation"]["task"] == "bug_fixing"
    assert d["user_state"]["emotion"] == "frustrated"
    assert d["context"]["active_project"] == "Saki"
