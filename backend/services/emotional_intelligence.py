"""
Saki Emotional Intelligence & Awareness Engine
Analyzes emotional states, dynamic social energy variables, and session awareness.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class EmotionalState(BaseModel):
    emotion: str = Field(default="neutral", description="Detected emotion category")
    intensity: float = Field(default=0.3, description="Emotional intensity 0.0 to 1.0")
    confidence: float = Field(default=0.7, description="Confidence in emotion assessment 0.0 to 1.0")
    cause: str = Field(default="casual conversation", description="Inferred cause of emotional state")
    needs: List[str] = Field(default_factory=lambda: ["friendly_interaction"], description="Inferred psychological or conversation needs")


class SocialEnergyState(BaseModel):
    energy: float = Field(default=0.75, description="Conversational energy level 0.0 to 1.0")
    warmth: float = Field(default=0.85, description="Warmth and empathetic resonance 0.0 to 1.0")
    playfulness: float = Field(default=0.60, description="Playful humor and banter 0.0 to 1.0")
    seriousness: float = Field(default=0.45, description="Depth and technical seriousness 0.0 to 1.0")


class SakiAwareness(BaseModel):
    current_activity: str = Field(default="chatting", description="coding, learning, chatting, debugging, venting, idle")
    current_project: Optional[str] = Field(default="Saki", description="Active project name")
    conversation_mode: str = Field(default="casual", description="casual, support, thinking, builder, vision")
    emotional_state: EmotionalState = Field(default_factory=EmotionalState)
    social_energy: SocialEnergyState = Field(default_factory=SocialEnergyState)
    last_model: str = Field(default="phi3:latest")
    session_duration: int = Field(default=0, description="Estimated session duration in minutes")
    recent_topic: str = Field(default="general")
    consecutive_frustrations: int = Field(default=0)


# Project name recognizers
KNOWN_PROJECTS = ["saki", "guardian ai", "webauditai", "webaudit", "portfolio", "nexus"]


# Pattern matchers for rich emotion detection
EMOTION_RULES = [
    # 1. Celebration / Breakthrough
    (
        r"\b(it works|finally works|fixed it|tests passed|yay|yes!|omg it worked|solved it|got it running|breakthrough)\b",
        "celebrating",
        0.90,
        0.88,
        "milestone breakthrough",
        ["celebration", "shared_joy"]
    ),
    # 2. Frustration / Debugging Roadblock
    (
        r"\b(stupid code|not working again|broken again|hate this bug|error again|failing again|why won't this work|so annoying|tired of this bug|frustrated)\b",
        "frustrated",
        0.85,
        0.85,
        "project debugging roadblock",
        ["acknowledgement", "practical_help", "calm_focus"]
    ),
    # 3. Anxiety / Overwhelmed
    (
        r"\b(overwhelmed|stressed|anxious|panic|so much to do|burnt out|burnout|drowning in work|too much pressure)\b",
        "overwhelmed",
        0.80,
        0.82,
        "high pressure and workload",
        ["calming", "reassurance", "prioritization"]
    ),
    # 4. Sadness / Loneliness
    (
        r"\b(lonely|feeling alone|sad|terrible day|feel down|nobody cares|feel like crying|depressed|heartbroken|rough day)\b",
        "sad",
        0.85,
        0.85,
        "emotional loneliness or rough day",
        ["validation", "warm_presence", "gentle_comfort"]
    ),
    # 5. Curiosity / Learning excitement
    (
        r"\b(how does|why does|fascinating|wondering about|can you explain|curious about|deep dive|teach me)\b",
        "curious",
        0.65,
        0.75,
        "intellectual curiosity",
        ["clarity", "depth", "encouragement"]
    ),
    # 6. Fatigue / Low energy
    (
        r"\b(exhausted|so tired|sleepy|need a break|brain is fried|no energy)\b",
        "tired",
        0.70,
        0.80,
        "mental or physical fatigue",
        ["gentle_tone", "rest_encouragement"]
    )
]


def extract_active_project(text: str, default_project: Optional[str] = "Saki") -> Optional[str]:
    """Detects active project from input text or keeps active context."""
    text_lower = text.lower()
    
    # 1. Match known projects first
    for proj in KNOWN_PROJECTS:
        if re.search(rf"\b{re.escape(proj)}\b", text_lower):
            return "Saki" if proj == "saki" else proj.title()

    # 2. Check explicit project phrases
    project_match = re.search(r"\b(?:working on|building|project)\s+([a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_-]+)?)", text_lower)
    if project_match:
        cand = project_match.group(1).strip()
        if cand not in ["a", "the", "my", "this", "it"]:
            return cand.title()
            
    return default_project


def detect_activity(text: str, has_code: bool, has_image: bool) -> str:
    """Classifies user activity context."""
    if has_image:
        return "visual_inspecting"
    if has_code or any(w in text.lower() for w in ["code", "bug", "fastapi", "react", "endpoint", "function", "error", "traceback"]):
        return "coding"
    if any(w in text.lower() for w in ["study", "explain", "what is", "why does", "concept", "algorithm"]):
        return "learning"
    if any(w in text.lower() for w in ["lonely", "sad", "vent", "feel like", "overwhelmed"]):
        return "venting"
    return "chatting"


def analyze_emotional_state(
    user_input: str,
    consecutive_frustrations: int = 0
) -> Tuple[EmotionalState, int]:
    """
    Evaluates the emotional state from user input and updates consecutive frustration count.
    """
    text_lower = user_input.lower()
    
    for pat, emotion, intensity, conf, cause, needs in EMOTION_RULES:
        if re.search(pat, text_lower):
            new_frustrations = consecutive_frustrations + 1 if emotion == "frustrated" else 0
            return EmotionalState(
                emotion=emotion,
                intensity=intensity,
                confidence=conf,
                cause=cause,
                needs=needs
            ), new_frustrations
            
    # Check general frustrated keywords
    if any(w in text_lower for w in ["stuck", "annoyed", "ugh", "grr", "cant get this"]):
        return EmotionalState(
            emotion="frustrated",
            intensity=0.65,
            confidence=0.75,
            cause="technical friction",
            needs=["acknowledgement", "practical_help"]
        ), consecutive_frustrations + 1

    return EmotionalState(
        emotion="neutral",
        intensity=0.30,
        confidence=0.70,
        cause="casual interaction",
        needs=["friendly_interaction"]
    ), 0


def calculate_social_energy(
    emotion: EmotionalState,
    activity: str,
    mode: str
) -> SocialEnergyState:
    """
    Modulates Social Energy variables (warmth, energy, playfulness, seriousness)
    to match the current conversational state and user needs.
    """
    # Baseline defaults
    warmth = 0.85
    energy = 0.70
    playfulness = 0.60
    seriousness = 0.45

    # Adjust based on emotion
    if emotion.emotion == "frustrated":
        warmth = 0.90
        energy = 0.65
        playfulness = 0.35  # dial down teasing when stuck
        seriousness = 0.75
    elif emotion.emotion in ["sad", "lonely", "overwhelmed"]:
        warmth = 0.95
        energy = 0.50
        playfulness = 0.15  # pure gentle presence
        seriousness = 0.60
    elif emotion.emotion == "celebrating":
        warmth = 0.90
        energy = 0.95
        playfulness = 0.85  # max hype & fun
        seriousness = 0.25
    elif emotion.emotion == "tired":
        warmth = 0.90
        energy = 0.40
        playfulness = 0.30
        seriousness = 0.30
    elif emotion.emotion == "curious":
        warmth = 0.80
        energy = 0.80
        playfulness = 0.50
        seriousness = 0.75

    # Adjust based on activity / mode
    if mode == "builder" or activity == "coding":
        seriousness = max(seriousness, 0.70)
        if emotion.emotion != "celebrating":
            playfulness = min(playfulness, 0.50)
    elif mode == "thinking" or activity == "learning":
        seriousness = max(seriousness, 0.75)
    elif mode == "casual":
        playfulness = max(playfulness, 0.65)
        energy = max(energy, 0.75)

    return SocialEnergyState(
        energy=round(energy, 2),
        warmth=round(warmth, 2),
        playfulness=round(playfulness, 2),
        seriousness=round(seriousness, 2)
    )


def build_awareness(
    query: str,
    mode: str,
    selected_model: str,
    previous_awareness: Optional[SakiAwareness] = None,
    has_code: bool = False,
    has_image: bool = False,
    session_start_time: Optional[float] = None
) -> SakiAwareness:
    """
    Constructs an updated SakiAwareness state representing Saki's live context.
    """
    prev_frustrations = previous_awareness.consecutive_frustrations if previous_awareness else 0
    prev_project = previous_awareness.current_project if previous_awareness else "Saki"
    
    emotional_state, new_frustrations = analyze_emotional_state(query, prev_frustrations)
    activity = detect_activity(query, has_code, has_image)
    project = extract_active_project(query, prev_project)
    social_energy = calculate_social_energy(emotional_state, activity, mode)
    
    # Calculate session duration
    duration = 0
    if session_start_time:
        duration = int((time.time() - session_start_time) / 60)
        
    return SakiAwareness(
        current_activity=activity,
        current_project=project,
        conversation_mode=mode,
        emotional_state=emotional_state,
        social_energy=social_energy,
        last_model=selected_model,
        session_duration=duration,
        recent_topic=activity,
        consecutive_frustrations=new_frustrations
    )
