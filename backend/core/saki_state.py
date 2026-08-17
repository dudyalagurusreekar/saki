"""
Saki Cognitive State Engine
Defines the multi-dimensional cognitive representation of the conversation,
user state, internal Saki posture, and confidence metrics.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    topic: str = Field(default="general", description="Current conversation topic")
    mode: str = Field(default="casual", description="casual, support, thinking, builder, vision")
    task: str = Field(default="casual_chat", description="bug_fixing, architecture_design, code_implementation, concept_learning, casual_chat, emotional_venting, vision_analysis")
    stage: str = Field(default="exploring", description="exploring, debugging, planning, implementing, reviewing, wrapping_up")


class UserCognitiveState(BaseModel):
    emotion: str = Field(default="neutral", description="Detected primary emotion")
    intensity: float = Field(default=0.3, description="Emotional intensity 0.0 to 1.0")
    confidence: float = Field(default=0.7, description="Emotion confidence 0.0 to 1.0")
    needs: List[str] = Field(default_factory=lambda: ["friendly_interaction"], description="Inferred user conversational needs")


class SakiInternalState(BaseModel):
    warmth: float = Field(default=0.85, description="Warmth & empathetic posture 0.0 to 1.0")
    playfulness: float = Field(default=0.60, description="Playful humor & wit 0.0 to 1.0")
    seriousness: float = Field(default=0.45, description="Technical focus & depth 0.0 to 1.0")
    verbosity: float = Field(default=0.50, description="Target response verbosity 0.0 (concise) to 1.0 (detailed)")


class ContextState(BaseModel):
    active_project: Optional[str] = Field(default="Saki", description="Active user project")
    last_model: str = Field(default="phi3:latest", description="Last model brain invoked")
    recent_topic: str = Field(default="general", description="Summary of recent topic")
    consecutive_frustrations: int = Field(default=0, description="Streak of frustrating turns")
    session_duration_minutes: int = Field(default=0, description="Minutes since session start")


class ConfidenceMetrics(BaseModel):
    routing_confidence: float = Field(default=0.90, description="Confidence in model selection")
    emotion_confidence: float = Field(default=0.75, description="Confidence in emotion detection")
    memory_relevance: float = Field(default=0.80, description="Relevance score of retrieved memories")


class SakiCognitiveState(BaseModel):
    conversation: ConversationState = Field(default_factory=ConversationState)
    user_state: UserCognitiveState = Field(default_factory=UserCognitiveState)
    saki_state: SakiInternalState = Field(default_factory=SakiInternalState)
    context: ContextState = Field(default_factory=ContextState)
    uncertainty: ConfidenceMetrics = Field(default_factory=ConfidenceMetrics)


def infer_task_and_stage(query: str, mode: str, is_coding: bool, has_image: bool) -> tuple[str, str]:
    """Infers the fine-grained task and conversational stage from user input."""
    q_lower = query.lower()
    
    if has_image:
        return "vision_analysis", "reviewing"
        
    if is_coding:
        if any(w in q_lower for w in ["fix", "error", "bug", "traceback", "failing", "broken", "500", "exception"]):
            return "bug_fixing", "debugging"
        if any(w in q_lower for w in ["architecture", "design", "structure", "plan", "how should we build"]):
            return "architecture_design", "planning"
        if any(w in q_lower for w in ["implement", "create", "write", "build", "component", "function"]):
            return "code_implementation", "implementing"
        return "bug_fixing", "debugging"

    if mode == "thinking":
        if any(w in q_lower for w in ["what is", "why does", "explain", "how does", "compare", "difference"]):
            return "concept_learning", "exploring"
        return "architecture_design", "planning"

    if mode == "support":
        return "emotional_venting", "exploring"

    if any(w in q_lower for w in ["done", "works now", "fixed it", "thanks", "bye"]):
        return "casual_chat", "wrapping_up"

    return "casual_chat", "exploring"
