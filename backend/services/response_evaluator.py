import re
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from backend.services.response_planner import ResponsePlan, AdaptiveLength
from backend.services.grounding_verifier import GroundingVerifierEngine, AnswerGroundingAssessment


class QualityStatus(str, Enum):
    PASS = "PASS"
    MINOR_ISSUE = "MINOR_ISSUE"
    REGENERATE = "REGENERATE"


class EvaluationResult(BaseModel):
    passed: bool = Field(default=True, description="Whether response passed quality standards")
    status: QualityStatus = Field(default=QualityStatus.PASS, description="PASS, MINOR_ISSUE, or REGENERATE")
    score: float = Field(default=1.0, description="Persona and quality score 0.0 to 1.0")
    persona_issues: List[str] = Field(default_factory=list, description="Identified persona or tone flaws")
    repaired_text: str = Field(description="Cleaned, polished response ready for delivery")
    needs_regeneration: bool = Field(default=False, description="Whether response was so degraded it requires regen")
    grounding_assessment: Optional[AnswerGroundingAssessment] = Field(default=None, description="Claim-level grounding verification")


# Internal leak patterns that should never reach the user
INTERNAL_LEAK_PATTERNS = [
    r"\[(?:Instruction|System|Developer|System Prompt|Developer Message)[^\]]*\]\n?",
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
    
    return cleaned


def evaluate_response(
    draft_text: str,
    plan: Optional[ResponsePlan] = None,
    mode: str = "casual",
    evidence_items: Optional[List[Any]] = None,
    evidence_package: Optional[Any] = None,
    action_decision: Optional[Any] = None,
    user_query: Optional[str] = None
) -> EvaluationResult:
    """
    Scans draft response for internal leaks, robotic tropes, and cleans layout for comfortable reading.
    In Sprint 7, also performs claim-level factual grounding against retrieved evidence.
    """
    if not draft_text or len(draft_text.strip()) == 0:
        return EvaluationResult(
            passed=False,
            status=QualityStatus.REGENERATE,
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

    # Step 5: Support Mode Quality & Validate-Before-Solve Enforcement
    if mode == "support" or (plan and getattr(plan, "validate_before_solve", False)):
        # Check for excessive bullet advice dumps in emotional mode
        bullet_count = len(re.findall(r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+", cleaned))
        if bullet_count >= 4:
            issues.append("excessive_advice_bullets_in_support_mode")
            penalty += 0.20
            # Simplify bullet list into natural prose paragraphs
            cleaned = re.sub(r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+", " ", cleaned)
            cleaned = format_comfortable_layout(cleaned)

        # Check for artificial human claims
        artificial_human_patterns = [
            (r"\bi (?:also )?cried when\b[^.!?]*[.!?]?", ""),
            (r"\bwhen i was human\b[^.!?]*[.!?]?", ""),
            (r"\bi have human feelings\b[^.!?]*[.!?]?", "")
        ]
        for pat, rep in artificial_human_patterns:
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                issues.append("artificial_human_claim")
                penalty += 0.20
                cleaned = re.sub(pat, rep, cleaned, flags=re.IGNORECASE).strip()

    # Step 6: Multilingual Quality & Unicode Integrity Check (Sprint 6)
    target_lang = getattr(plan, "language", None) or "en"
    if "\ufffd" in cleaned:
        issues.append("unicode_replacement_character_detected")
        penalty += 0.25
        cleaned = cleaned.replace("\ufffd", "")

    # Check for unwanted language mismatch on non-code responses
    has_code = "```" in cleaned
    if not has_code and len(cleaned) > 20:
        if target_lang == "te" and not re.search(r'[\u0C00-\u0C7F]', cleaned):
            issues.append("telugu_language_mismatch")
            penalty += 0.20
        elif target_lang == "kn" and not re.search(r'[\u0C80-\u0CFF]', cleaned):
            issues.append("kannada_language_mismatch")
            penalty += 0.20

    # Step 7: Check if text became empty after removing leaks/cliches
    if len(cleaned) < 5:
        issues.append("response_became_empty_after_cleanse")
        if target_lang == "te":
            cleaned = "నేను వింటున్నాను. మనం కలిసి పరిష్కరిద్దాం! 🌸" if mode == "support" else "సరే! మనం ప్రారంభిద్దాం. 🚀"
        elif target_lang == "kn":
            cleaned = "ನಾನು ಕೇಳುತ್ತಿದ್ದೇನೆ. ನಾವಿಬ್ಬರೂ ಇದನ್ನು ಪರಿಹರಿಸೋಣ! 🌸" if mode == "support" else "ಸರಿ! ನಾವು ಪ್ರಾರಂಭಿಸೋಣ. 🚀"
        else:
            cleaned = "I hear you. Take a breath—I'm right here with you. 🌸" if mode == "support" else "Got it! Let's jump right into it. 🚀"

    # Step 8: Claim-Level Grounding Verification
    grounding_assessment = None
    if evidence_items or evidence_package or (action_decision and getattr(action_decision, "requires_world_access", False)):
        grounding_assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=cleaned,
            evidence_items=evidence_items,
            evidence_package=evidence_package,
            action_decision=action_decision,
            user_query=user_query
        )
    score = max(0.0, round(1.0 - penalty, 2))
    needs_regen = (score < 0.30) or ("empty_response" in issues)
    passed = score >= 0.50

    if needs_regen:
        status = QualityStatus.REGENERATE
    elif len(issues) > 0:
        status = QualityStatus.MINOR_ISSUE
    else:
        status = QualityStatus.PASS

    return EvaluationResult(
        passed=passed,
        status=status,
        score=score,
        persona_issues=issues,
        repaired_text=cleaned,
        needs_regeneration=needs_regen,
        grounding_assessment=grounding_assessment
    )
