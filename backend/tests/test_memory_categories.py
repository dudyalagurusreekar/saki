import pytest
from backend.services.memory_service import (
    normalize_memory,
    get_categorized_memories,
    extract_memories,
    retrieve_memories,
    build_smart_memory_context,
    retrieve_project_memories
)

def test_categorized_memories_structure():
    raw_memory = {
        "memories": [
            {"type": "PROJECT", "content": "User is building Saki AI"},
            {"type": "PREFERENCE", "content": "User prefers dark mode"},
            {"type": "FACT", "content": "User is a teen developer"},
            {"type": "DECISION", "content": "Decided to use FastAPI for backend"},
            {"type": "PROGRESS", "content": "Implemented persona engine"},
            {"type": "PATTERN", "content": "User tends to change 3 things at once"}
        ]
    }
    categorized = get_categorized_memories(raw_memory)
    assert len(categorized["projects"]) == 1
    assert len(categorized["preferences"]) == 1
    assert len(categorized["facts"]) == 1
    assert len(categorized["decisions"]) == 1
    assert len(categorized["progress"]) == 1
    assert len(categorized["patterns"]) == 1

def test_extract_memories_decisions_and_projects():
    extracted = extract_memories("We decided to use FastAPI for the backend instead of Flask")
    assert any(m["type"] == "DECISION" for m in extracted)
    assert any("FastAPI" in m["content"] for m in extracted)

def test_extract_memories_progress():
    extracted = extract_memories("I finally fixed the routing bug in orchestrator")
    assert any(m["type"] == "PROGRESS" for m in extracted)

def test_retrieve_project_memories():
    raw_memory = {
        "memories": [
            {"type": "PROJECT", "content": "User is building Saki, a local AI"},
            {"type": "PROJECT", "content": "User is working on WebAuditAI"},
            {"type": "PREFERENCE", "content": "User likes Python"}
        ]
    }
    saki_mems = retrieve_project_memories(raw_memory, "Saki")
    assert len(saki_mems) == 1
    assert "Saki" in saki_mems[0]["content"]

def test_build_smart_memory_context():
    raw_memory = {
        "memories": [
            {"type": "PROJECT", "content": "User is building Saki companion", "score": 10},
            {"type": "DECISION", "content": "Decided on 5 local models architecture", "score": 9}
        ]
    }
    context = build_smart_memory_context(raw_memory, query="How does our Saki architecture work?", active_mode="builder", active_project="Saki")
    assert "Saki" in context
    assert "PROJECT" in context or "DECISION" in context
