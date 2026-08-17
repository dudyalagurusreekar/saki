"""
Saki Response Evaluator Engine — Response Sanitizer & Quality Gate
Evaluates draft model responses to enforce Saki's persona integrity,
strip internal metadata leakage, remove robotic assistant cliches,
prevent prompt repetition, and ensure clean, comfortable representation.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.services.response_planner import ResponsePlan


class EvaluationResult(BaseModel):
    passed: bool = Field(default=True, description="Whether response passed quality standards")
    score: float = Field(default=1.0, description="Persona and quality score 0.0 to 1.0")
    persona_issues: List[str] = Field(default_factory=list, description="Identified persona or tone flaws")
    repaired_text: str = Field(description="Cleaned, polished response ready for delivery")
    needs_regeneration: bool = Field(default=False, description="Whether response was so degraded it requires regen")


# Internal leak patterns that should never reach the user
INTERNAL_LEAK_PATTERNS = [
    r"\[(?:Instruction|System|Developer|System Prompt|Developer Message)\][\s\S]*?(?=\n\n|\Z)",
    r"<\/?(?:think|thought|internal)>[\s\S]*?<\/(?:think|thought|internal)>",
    r"<\/?(?:think|thought|internal)>",
    r"(?:Emotional Context|Detected Emotion|User Needs|Response Strategy|Conversational Continuity|Durable Memory|Project Context|Routing Decision|Model Selection|Internal Analysis|Chain of Thought|Confidence Score)\s*[:：][^\n]*\n?",
    r"(?:Tone Modulation|Internal Habit Guidance|Known Context|Emotional Context)\s*\([^)]*\)\s*[:：]?",
    r"According to my (?:instructions|system prompt|durable memory|internal memory|programming)[^.!?]*[.!?]?",
    r"My core personality is[^.!?]*[.!?]?",
    r"My detected emotional state is[^.!?]*[.!?]?",
    r"As per my instructions[^.!?]*[.!?]?"
]

ROBOTIC_CLICHES = [
    (r"\bhow (?:can|may) i (?:assist|help) you (?:today)?\s*\?*", ""),
    (r"\bi am an ai (?:model|assistant|language model|companion)[^.!?]*[.!?]?", ""),
    (r"\bas an ai (?:model|assistant|language model|companion)?[^,.]*[,.]?", ""),
    (r"\bi apologize for (?:any|the) inconvenience[^.!?]*[.!?]?", ""),
    (r"\bfeel free to ask (?:me )?(?:any|further|more) questions[^.!?]*[.!?]?", ""),
    (r"\bplease let me know if you (?:need|have) (?:anything|any other questions)[^.!?]*[.!?]?", ""),
    (r"\bi'm here to (?:help|assist) you[^.!?]*[.!?]?", ""),
    (r"\bi'm here for you\b\.?", ""),
    (r"\bit is important to remember that[^.!?]*[.!?]?", ""),
    (r"\bhere are (?:some|a few|10|ten|5|five) steps (?:you can|to) take[^:.]*[:.]?", "")
]

SPEAKER_PREFIXES = [
    r"^saki\s*[-:：]\s*",
    r"^assistant\s*[-:：]\s*",
    r"^ai\s*[-:：]\s*",
    r"^\[saki\]\s*[-:：]?\s*",
    r"^\[assistant\]\s*[-:：]?\s*"
]


def clean_speaker_tags(text: str) -> str:
    """Strips leading speaker tags like Saki: or Assistant: or AI:"""
    cleaned = text.strip()
    for prefix in SPEAKER_PREFIXES:
        cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def sanitize_internal_leaks(text: str) -> str:
    """Strips internal system prompt leaks, chain-of-thought, or metadata tags."""
    cleaned = text
    for pattern in INTERNAL_LEAK_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def format_comfortable_layout(text: str) -> str:
    """
    Ensures clean, comfortable text presentation without dumping walls of text
    or having weird multiple empty lines.
    """
    # Normalize line breaks
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    # Collapse 3+ consecutive line breaks into 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    
    # Ensure code blocks have nice spacing
    cleaned = re.sub(r"([^\n])(```[a-zA-Z0-9_#+-]*)", r"\1\n\n\2", cleaned)
    cleaned = re.sub(r"(```)\n*([^\n`])", r"\1\n\2", cleaned)
    
    return cleaned


def evaluate_response(
    draft_text: str,
    plan: Optional[ResponsePlan] = None,
    mode: str = "casual"
) -> EvaluationResult:
    """
    Scans draft response for internal leaks, robotic tropes, and cleans layout for comfortable reading.
    """
    if not draft_text or len(draft_text.strip()) == 0:
        return EvaluationResult(
            passed=False,
            score=0.0,
            persona_issues=["empty_response"],
            repaired_text="Hmm, my thoughts drifted for a second. What were we looking at? 🌸",
            needs_regeneration=True
        )

    # Step 1: Strip speaker tags and internal leaks
    cleaned = clean_speaker_tags(draft_text)
    cleaned = sanitize_internal_leaks(cleaned)
    
    issues = []
    penalty = 0.0

    # Step 2: Check for robotic tropes and cliches
    for pattern, replacement in ROBOTIC_CLICHES:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            issues.append(f"robotic_cliche: {pattern}")
            penalty += 0.15
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE).strip()

    # Step 3: Format comfortable layout
    cleaned = format_comfortable_layout(cleaned)

    # Step 4: Check depth & conciseness if requested
    words = cleaned.split()
    if plan and plan.depth == "concise" and len(words) > 85 and mode == "casual":
        issues.append("too_verbose_for_casual_mode")
        penalty += 0.10

    # Step 5: Check if text became empty after removing leaks/cliches
    if len(cleaned) < 5:
        issues.append("response_became_empty_after_cleanse")
        cleaned = "Got it! Let's jump right into it. 🚀"

    score = max(0.0, round(1.0 - penalty, 2))
    passed = score >= 0.50

    return EvaluationResult(
        passed=passed,
        score=score,
        persona_issues=issues,
        repaired_text=cleaned,
        needs_regeneration=(score < 0.30)
    )
