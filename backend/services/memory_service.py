import json
from pathlib import Path
from backend.core.config import settings

MEMORY_PATH = Path("data/memory.json")


def load_memory():
    if not MEMORY_PATH.exists():
        return {"conversation_history": []}

    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(memory):
    MEMORY_PATH.parent.mkdir(exist_ok=True)

    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def update_memory(memory, user, response):
    memory["conversation_history"].append({
        "user": user,
        "saki": response
    })

    memory["conversation_history"] = memory["conversation_history"][-settings.MAX_MEMORY:]

    save_memory(memory)