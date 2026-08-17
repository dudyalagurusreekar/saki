"""
Saki Learning Service
Detects direct user corrections and instructions, converting them into durable
routing policies and behavioral preferences so Saki improves continuously through interaction.
"""

import re
from typing import Optional, Dict, Any, List
from backend.core.config import settings


CORRECTION_PATTERNS = [
    # Routing overrides
    (
        r"\b(?:don't|dont|do not)\s+(?:route|send|use)\s+.*?\b(?:to\s+)?(hermes|phi3|qwen3|coder|gemma)\b.*?\buse\s+(hermes|phi3|qwen3|coder|gemma)\b",
        "ROUTING_OVERRIDE",
        "Prefer {} over {} for related queries"
    ),
    (
        r"\b(?:always|prefer to)\s+use\s+(hermes|phi3|qwen3|coder|gemma)\s+(?:for|when)\s+([^.!?]+)",
        "ROUTING_OVERRIDE",
        "Always use {} for {}"
    ),
    # Verbosity / Length
    (
        r"\b(?:keep|make)\s+(?:your\s+)?(?:answers|responses|it)\s+(shorter|more concise|brief|longer|more detailed)\b",
        "STYLE_PREFERENCE",
        "User prefers {} responses"
    ),
    # Coding / Architecture rules
    (
        r"\b(?:always|never)\s+use\s+([a-zA-Z0-9_-]+)\s+in\s+this\s+project\b",
        "DECISION",
        "Project rule: {}"
    )
]


def detect_user_correction(query: str) -> Optional[Dict[str, Any]]:
    """
    Scans user input for explicit workflow or preference corrections.
    """
    q_lower = query.lower()
    
    for pattern, rule_type, template in CORRECTION_PATTERNS:
        match = re.search(pattern, q_lower)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                content = template.format(groups[1], groups[0])
            elif len(groups) == 1:
                content = template.format(groups[0])
            else:
                content = template.format(*groups)
                
            return {
                "type": rule_type,
                "content": content,
                "importance": 9,
                "confidence": 9.5,
                "metadata": {"source": "user_correction"}
            }
            
    return None


def apply_learned_policies(
    query: str,
    default_model: str,
    memory: dict
) -> str:
    """
    Checks stored decision and preference memories for active model overrides.
    """
    memories = memory.get("memories", [])
    decisions = [m for m in memories if m.get("type") in {"DECISION", "ROUTING_OVERRIDE", "PREFERENCE"}]
    
    q_lower = query.lower()
    
    for d in decisions:
        content_lower = d.get("content", "").lower()
        if "prefer qwen3 over hermes" in content_lower and default_model == settings.MODEL_HERMES:
            return settings.MODEL_QWEN3
        if "always use coder for" in content_lower and any(w in q_lower for w in ["python", "fastapi", "react", "code"]):
            return settings.MODEL_CODER

    return default_model
