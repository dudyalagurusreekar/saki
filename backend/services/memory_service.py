import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from backend.core.config import settings


MEMORY_PATH = Path("data/memory.json")

MEMORY_TYPES = {
    "FACT",
    "GOAL",
    "PROJECT",
    "SKILL",
    "PREFERENCE",
    "EVENT",
    "INSIGHT",
    "PERSONALITY",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "do",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
    "you",
    "your",
}


def _now() -> float:
    return time.time()


def _default_memory() -> dict[str, Any]:
    return {
        "name": None,
        "interests": [],
        "recent_mood": "neutral",
        "conversation_history": [],
        "memories": [],
        "user_model": {
            "learning_style": None,
            "career_goal": None,
            "project_focus": 0.0,
            "curiosity": 0.0,
            "technical_depth": 0.0,
            "persistence": 0.0,
            "updated_at": None,
        },
        "reflections": [],
        "last_interaction_time": None,
    }


def _tokenize(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 2 and word not in STOP_WORDS
    }


def _canonical(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _clean_fragment(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip(" .,!?:;\"'"))
    return text[:180]


def _memory_score(memory: dict[str, Any]) -> float:
    last_seen = float(memory.get("last_seen") or memory.get("created_at") or _now())
    age_days = max((_now() - last_seen) / 86400, 0)
    recency = max(0.0, 10.0 - age_days)
    return round(
        float(memory.get("importance", 0))
        + float(memory.get("frequency", 0))
        + recency
        + float(memory.get("confidence", 0)),
        2,
    )


def _normalize_memory_item(memory: dict[str, Any]) -> dict[str, Any] | None:
    content = _clean_fragment(str(memory.get("content", "")))
    memory_type = str(memory.get("type", "FACT")).upper()

    if not content:
        return None

    if memory_type not in MEMORY_TYPES:
        memory_type = "FACT"

    normalized = {
        "id": memory.get("id") or str(uuid.uuid4()),
        "type": memory_type,
        "content": content,
        "importance": int(memory.get("importance", 5)),
        "confidence": float(memory.get("confidence", 7)),
        "frequency": int(memory.get("frequency", 1)),
        "created_at": float(memory.get("created_at") or _now()),
        "last_seen": float(memory.get("last_seen") or memory.get("created_at") or _now()),
        "source": memory.get("source", "conversation"),
        "metadata": memory.get("metadata", {}),
    }
    normalized["score"] = _memory_score(normalized)
    return normalized


def normalize_memory(memory: dict[str, Any] | None) -> dict[str, Any]:
    normalized = _default_memory()

    if isinstance(memory, dict):
        normalized.update(memory)

    normalized["conversation_history"] = list(normalized.get("conversation_history") or [])
    normalized["memories"] = [
        item
        for item in (
            _normalize_memory_item(memory_item)
            for memory_item in normalized.get("memories", [])
            if isinstance(memory_item, dict)
        )
        if item is not None
    ]

    user_model = _default_memory()["user_model"]
    if isinstance(normalized.get("user_model"), dict):
        user_model.update(normalized["user_model"])
    normalized["user_model"] = user_model

    if normalized.get("name") and not any(
        m["type"] == "FACT" and "name is" in m["content"].lower()
        for m in normalized["memories"]
    ):
        normalized["memories"].append(
            _normalize_memory_item(
                {
                    "type": "FACT",
                    "content": f"User's name is {normalized['name']}",
                    "importance": 8,
                    "confidence": 8,
                    "source": "profile",
                }
            )
        )

    for interest in normalized.get("interests", []) or []:
        content = f"User is interested in {interest}"
        if not any(_canonical(m["content"]) == _canonical(content) for m in normalized["memories"]):
            normalized["memories"].append(
                _normalize_memory_item(
                    {
                        "type": "PREFERENCE",
                        "content": content,
                        "importance": 6,
                        "confidence": 7,
                        "source": "profile",
                    }
                )
            )

    normalized["memories"] = sorted(
        normalized["memories"],
        key=lambda item: item.get("score", 0),
        reverse=True,
    )
    return normalized


def load_memory() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        return _default_memory()

    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return normalize_memory(json.load(f))


def save_memory(memory: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(exist_ok=True)
    memory = normalize_memory(memory)

    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=True)


def _candidate(memory_type: str, content: str, importance: int, confidence: float) -> dict[str, Any] | None:
    content = _clean_fragment(content)
    if len(content) < 4:
        return None

    return {
        "type": memory_type,
        "content": content,
        "importance": importance,
        "confidence": confidence,
        "frequency": 1,
        "created_at": _now(),
        "last_seen": _now(),
        "source": "conversation",
        "metadata": {},
    }


def extract_memories(user_input: str, response: str = "") -> list[dict[str, Any]]:
    text = _clean_fragment(user_input)
    lower = text.lower()
    candidates: list[dict[str, Any]] = []

    patterns = [
        (r"\bmy name is ([a-zA-Z][a-zA-Z .'-]{1,60})", "FACT", "User's name is {}", 9, 9),
        (r"\bi am studying ([^.!?]{3,120})", "SKILL", "User studies {}", 8, 8),
        (r"\bi study ([^.!?]{3,120})", "SKILL", "User studies {}", 8, 8),
        (r"\bi am learning ([^.!?]{3,120})", "SKILL", "User is learning {}", 8, 8),
        (r"\bi want to ([^.!?]{3,120})", "GOAL", "User wants to {}", 8, 7),
        (r"\bmy goal is to ([^.!?]{3,120})", "GOAL", "User's goal is to {}", 9, 8),
        (r"\bi prefer ([^.!?]{3,120})", "PREFERENCE", "User prefers {}", 7, 8),
        (r"\bi like ([^.!?]{3,120})", "PREFERENCE", "User likes {}", 6, 7),
        (r"\bi am building ([^.!?]{3,120})", "PROJECT", "User is building {}", 9, 8),
        (r"\bi am working on ([^.!?]{3,120})", "PROJECT", "User is working on {}", 8, 8),
        (r"\bmy project is ([^.!?]{3,120})", "PROJECT", "User's project is {}", 9, 8),
    ]

    for pattern, memory_type, template, importance, confidence in patterns:
        for match in re.finditer(pattern, lower, flags=re.IGNORECASE):
            value = _clean_fragment(match.group(1))
            item = _candidate(memory_type, template.format(value), importance, confidence)
            if item:
                candidates.append(item)

    if any(word in lower for word in ["saki", "local ai", "ai companion"]):
        item = _candidate("PROJECT", "User is building Saki, a local-first AI companion", 10, 8)
        if item:
            candidates.append(item)

    if any(word in lower for word in ["hands-on", "project based", "implementation", "practical"]):
        item = _candidate("INSIGHT", "User learns best through practical implementation", 8, 7)
        if item:
            candidates.append(item)

    if any(word in lower for word in ["sad", "lonely", "alone", "anxious", "stressed", "low"]):
        item = _candidate("EVENT", "User expressed a low or lonely mood recently", 6, 6)
        if item:
            candidates.append(item)

    return candidates


def _upsert_memory(memory: dict[str, Any], candidate: dict[str, Any]) -> None:
    normalized_candidate = _normalize_memory_item(candidate)
    if normalized_candidate is None:
        return

    candidate_key = (_canonical(normalized_candidate["type"]), _canonical(normalized_candidate["content"]))

    for existing in memory["memories"]:
        existing_key = (_canonical(existing["type"]), _canonical(existing["content"]))
        if existing_key == candidate_key:
            existing["frequency"] = int(existing.get("frequency", 1)) + 1
            existing["confidence"] = min(10.0, float(existing.get("confidence", 0)) + 0.25)
            existing["importance"] = max(
                int(existing.get("importance", 0)),
                int(normalized_candidate.get("importance", 0)),
            )
            existing["last_seen"] = _now()
            existing["score"] = _memory_score(existing)
            return

    memory["memories"].append(normalized_candidate)


def _update_user_model(memory: dict[str, Any]) -> None:
    memories = memory.get("memories", [])
    projects = [m for m in memories if m["type"] == "PROJECT"]
    goals = [m for m in memories if m["type"] == "GOAL"]
    skills = [m for m in memories if m["type"] == "SKILL"]
    insights = [m for m in memories if m["type"] == "INSIGHT"]

    model = memory.get("user_model") or {}
    model["project_focus"] = min(10.0, round(sum(m.get("frequency", 1) for m in projects) / 2, 1))
    model["technical_depth"] = min(10.0, round((len(skills) * 1.5) + (len(projects) * 1.0), 1))
    model["curiosity"] = min(10.0, round((len(memory.get("interests", [])) * 1.0) + len(goals), 1))
    model["persistence"] = min(10.0, round(max((m.get("frequency", 1) for m in projects), default=0), 1))
    model["updated_at"] = _now()

    if goals:
        model["career_goal"] = sorted(goals, key=lambda item: item.get("score", 0), reverse=True)[0]["content"]

    if any("implementation" in m["content"].lower() for m in insights):
        model["learning_style"] = "Hands-on"

    memory["user_model"] = model


def update_memory(memory: dict[str, Any], user: str, response: str) -> None:
    memory = normalize_memory(memory)
    memory["conversation_history"].append({"user": user, "saki": response})
    memory["conversation_history"] = memory["conversation_history"][-settings.MAX_MEMORY :]

    for candidate in extract_memories(user, response):
        _upsert_memory(memory, candidate)

    memory["memories"] = sorted(
        memory["memories"],
        key=lambda item: item.get("score", 0),
        reverse=True,
    )[: settings.MAX_DURABLE_MEMORIES]
    memory["last_interaction_time"] = _now()
    _update_user_model(memory)
    save_memory(memory)


def retrieve_memories(memory: dict[str, Any], query: str, limit: int = 6) -> list[dict[str, Any]]:
    memory = normalize_memory(memory)
    query_tokens = _tokenize(query)
    ranked: list[tuple[float, dict[str, Any]]] = []

    for item in memory.get("memories", []):
        content_tokens = _tokenize(item["content"])
        overlap = len(query_tokens & content_tokens)
        type_boost = 2 if item["type"] in {"GOAL", "PROJECT", "PREFERENCE", "INSIGHT"} else 0
        relevance = overlap * 5 + float(item.get("score", 0)) * 0.25 + type_boost

        if overlap or item["type"] in {"GOAL", "PROJECT", "PREFERENCE"}:
            ranked.append((relevance, item))

    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:limit]]


def build_memory_context(memory: dict[str, Any], query: str, limit: int = 6) -> str:
    relevant = retrieve_memories(memory, query, limit=limit)
    if not relevant:
        return "No durable memories are relevant yet."

    lines = []
    for item in relevant:
        lines.append(
            f"- {item['type']}: {item['content']} "
            f"(importance {item['importance']}, confidence {item['confidence']})"
        )
    return "\n".join(lines)
