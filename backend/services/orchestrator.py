import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.config import settings
from backend.services.emotional_support_service import (
    SupportAssessment,
    SupportAssessmentEngine,
    SupportType,
    HermesActivationLevel
)
from backend.services.emotional_intelligence import (
    EmotionalState,
    SocialEnergyState,
    SakiAwareness,
    calculate_social_energy,
    detect_activity,
    extract_active_project,
    build_awareness
)
from backend.core.saki_state import (
    SakiCognitiveState,
    ConversationState,
    UserCognitiveState,
    SakiInternalState,
    ContextState,
    ConfidenceMetrics,
    infer_task_and_stage
)
from backend.services.learning_service import apply_learned_policies
from backend.services.action_engine import ActionDecision, decide_action
from backend.services.temporal_service import TemporalService


from enum import Enum
from dataclasses import dataclass, field
import time


class ConversationPosition(str, Enum):
    OPENING = "OPENING"
    FOLLOW_UP = "FOLLOW_UP"
    EXPLORATION = "EXPLORATION"
    DEEP_DISCUSSION = "DEEP_DISCUSSION"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    EMOTIONAL_PROCESSING = "EMOTIONAL_PROCESSING"
    CLARIFICATION = "CLARIFICATION"
    DECISION_MAKING = "DECISION_MAKING"
    CLOSING = "CLOSING"


@dataclass
class ModelSelectionContext:
    """Unified context passed into Saki model scoring and orchestration engine."""
    current_message: str
    recent_conversation: List[Dict[str, Any]] = field(default_factory=list)
    current_topic: str = "general"
    current_project: str = "Saki"
    primary_intent: str = "general"
    secondary_intent: Optional[str] = None
    complexity: str = "medium"
    emotion: str = "neutral"
    emotion_intensity: float = 0.0
    support_need: float = 0.0
    support_level: str = "none"
    solution_readiness: float = 0.5
    conversation_position: ConversationPosition = ConversationPosition.EXPLORATION
    detected_language: str = "en"
    output_language: str = "en"
    is_code_mixed: bool = False
    vision_required: bool = False
    coding_required: bool = False
    memory_required: bool = False
    rag_required: bool = False
    previous_model: Optional[str] = None
    previous_model_confidence: float = 0.85
    current_model_state: str = "IDLE"
    resource_state: Dict[str, Any] = field(default_factory=dict)


def infer_conversation_position(
    query_lower: str,
    recent_history: List[Dict[str, Any]],
    support_need: float,
    is_coding: bool
) -> ConversationPosition:
    """Infers conversational position from context and message dynamics."""
    history_len = len(recent_history or [])
    if history_len == 0 and any(query_lower.startswith(g) for g in ["hi", "hello", "hey", "good morning", "good evening", "namaskaram", "namaskara"]):
        return ConversationPosition.OPENING
    if any(kw in query_lower for kw in ["bye", "goodbye", "good night", "see you", "that's all", "thank you so much", "done for today"]):
        return ConversationPosition.CLOSING
    if support_need >= 0.60:
        return ConversationPosition.EMOTIONAL_PROCESSING
    if is_coding:
        return ConversationPosition.PROBLEM_SOLVING
    if any(query_lower.startswith(w) for w in ["what about", "and also", "then how", "next", "also", "furthermore"]):
        return ConversationPosition.FOLLOW_UP
    if any(kw in query_lower for kw in ["what should i choose", "decide between", "which one is better", "should i use"]):
        return ConversationPosition.DECISION_MAKING
    if any(kw in query_lower for kw in ["what do you mean", "could you clarify", "explain more"]):
        return ConversationPosition.CLARIFICATION
    if history_len >= 4:
        return ConversationPosition.DEEP_DISCUSSION
    return ConversationPosition.EXPLORATION


def _apply_temporal_tone(awareness) -> None:
    """Apply time-of-day tone adjustments to awareness social energy in-place."""
    adjustments = TemporalService.get_tone_adjustments()
    if awareness and awareness.social_energy:
        se = awareness.social_energy
        se.energy = max(0.0, min(1.0, se.energy + adjustments.get("energy", 0.0)))
        se.warmth = max(0.0, min(1.0, se.warmth + adjustments.get("warmth", 0.0)))
        se.playfulness = max(0.0, min(1.0, se.playfulness + adjustments.get("playfulness", 0.0)))
        se.seriousness = max(0.0, min(1.0, se.seriousness + adjustments.get("seriousness", 0.0)))


def _temporal_context_fields() -> dict:
    """Return temporal fields for ContextState construction."""
    ctx = TemporalService.get_temporal_context()
    return {
        "current_time_of_day": ctx.time_of_day,
        "is_weekend": ctx.is_weekend,
        "session_start_time": ctx.datetime_iso,
    }


class RoutingDecision(BaseModel):
    selected_model: str = Field(description="Ollama model tag to execute")
    task_type: str = Field(description="simple_chat, emotional_support, coding_task, vision_analysis, general_reasoning, mixed_support_practical")
    conversation_mode: str = Field(default="casual", description="casual, support, thinking, builder, vision")
    complexity: str = Field(description="low, medium, high, complex")
    emotional_importance: str = Field(description="low, medium, high")
    detected_emotion: str = Field(default="neutral", description="neutral, sad, anxious, frustrated, excited, celebrating, etc.")
    emotional_state: EmotionalState = Field(default_factory=EmotionalState)
    support_assessment: Optional[SupportAssessment] = None
    social_energy: SocialEnergyState = Field(default_factory=SocialEnergyState)
    awareness: Optional[SakiAwareness] = None
    cognitive_state: Optional[SakiCognitiveState] = None
    action_decision: Optional[ActionDecision] = None
    vision_required: bool = Field(default=False)
    coding_required: bool = Field(default=False)
    memory_required: bool = Field(default=False)
    rag_required: bool = Field(default=False)
    confidence: float = Field(description="Routing confidence score 0.0 to 1.0")
    support_score: float = Field(default=0.0, description="Calibrated support need score 0.0 to 1.0")
    support_level: str = Field(default="none", description="none, low, moderate, high")
    primary_intent: str = Field(default="general", description="Primary detected intent")
    secondary_intent: Optional[str] = Field(default=None, description="Secondary intent")
    reason: str = Field(description="Human-readable justification for the decision")
    should_switch_model: bool = Field(default=False)
    should_stop_after_response: bool = Field(default=True)
    keep_loaded: bool = Field(default=False)


# Standard simple greetings / short voice triggers
GREETING_KEYWORDS = {
    "hi", "hello", "hey", "good morning", "good evening", "good night", 
    "thanks", "thank you", "okay", "ok", "cool", "got it", "byebye", "bye",
    "status", "ping", "are you there", "yes", "no"
}

# Code & programming indicators
CODING_PATTERNS = [
    r"```[a-zA-Z]*",
    r"\b(traceback|stack trace|exception|syntaxerror|nullpointerexception|typeerror|valueerror|indexerror|connection error|runtime error)\b",
    r"\b(fix|debug|refactor|write a function|create a component|implement|script|fastapi|react|next\.js|python|java|typescript|javascript|dockerfile|sql query|websocket|backend|frontend|api|endpoint|middleware|auth|authentication|database|schema)\b",
    r"\b(endpoint failing|code error|bug in|compilation error|npm error|pip error|500 internal server error|next step for|how to implement|code snippet)\b"
]

# Conceptual/educational question indicators
CONCEPTUAL_PATTERNS = [
    r"\bwhat is\b",
    r"\bexplain\b",
    r"\bdifference between\b",
    r"\bwhy does\b",
    r"\bhow does\b",
    r"\bhistory of\b",
    r"\bdescribe\b",
    r"\bcompare\b"
]

# Personal memory inquiry patterns
MEMORY_PATTERNS = [
    r"\b(do you remember|what did i say|what is my name|my preferences|who am i|our last chat|remind me|my project architecture|what are my goals)\b"
]


class SakiModelOrchestrator:
    """
    Saki Cognitive Model Orchestrator & Mode Router.
    Decouples task determination from emotional tone modulation, applies learned policies,
    evaluates multi-signal support assessments, and coordinates model selection.
    """

    @staticmethod
    def classify_request(
        query: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        previous_model: Optional[str] = None,
        previous_awareness: Optional[SakiAwareness] = None,
        memory_data: Optional[Dict[str, Any]] = None,
        is_voice_mode: bool = False,
        recent_history: Optional[List[Dict[str, Any]]] = None
    ) -> RoutingDecision:
        query_text = (query or "").strip()
        query_lower = query_text.lower()
        attachments = attachments or []
        recent_history = recent_history or (memory_data.get("conversation_history", []) if memory_data else [])

        # 1. Multi-Signal Support Assessment & Temporal Emotion Tracking
        support_assessment = SupportAssessmentEngine.evaluate(
            user_input=query_text,
            recent_history=recent_history,
            previous_assessment=previous_awareness.support_assessment if previous_awareness else None,
            active_project=previous_awareness.current_project if previous_awareness else "Saki"
        )
        detected_emotion = support_assessment.emotion
        emotional_importance = "high" if support_assessment.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD else ("medium" if support_assessment.support_need >= settings.HERMES_SUPPORT_MODERATE_THRESHOLD else "low")
        support_level_str = support_assessment.activation_level.value.lower()

        # 2. Detect Vision Requirement (Mode: vision -> Gemma 3)
        has_image_attachment = any(
            att.get("type") in ["image", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", "image/png", "image/jpeg", "image/webp"] 
            or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            or str(att.get("path", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            for att in (attachments or [])
        )
        vision_keywords = ["screenshot", "this image", "in this picture", "this diagram", "read text from photo", "visual layout"]
        has_vision_keyword = any(kw in query_lower for kw in vision_keywords)
        vision_required = has_image_attachment or (has_vision_keyword and len(attachments) > 0)

        if vision_required:
            is_visual_coding = False
            for pat in CODING_PATTERNS:
                if re.search(pat, query_lower):
                    is_visual_coding = True
                    break
            if any(kw in query_lower for kw in ["fix this code", "fix the code", "debug this code", "write code", "implement", "python error", "react component", "write script"]):
                is_visual_coding = True

            diagram_keywords = ["architecture diagram", "flowchart logic", "system design diagram", "mathematical proof", "deduce from chart"]
            is_diagram_reasoning = any(kw in query_lower for kw in diagram_keywords)

            if is_visual_coding:
                selected_model = settings.MODEL_CODER
                conv_mode = "builder"
                task_type = "visual_coding_task"
                coding_required = True
                reason = "Screenshot contains code/error; Gemma 3 extracts visual text/UI and Qwen 2.5 Coder handles implementation."
            elif is_diagram_reasoning:
                selected_model = settings.MODEL_QWEN3
                conv_mode = "thinking"
                task_type = "visual_reasoning"
                coding_required = False
                reason = "Diagram/logic image; Gemma 3 extracts visual structures and Qwen 3 handles deep reasoning."
            else:
                selected_model = settings.MODEL_GEMMA
                conv_mode = "vision"
                task_type = "vision_analysis"
                coding_required = False
                reason = "Request requires visual analysis model (Gemma 3) for image or screenshot inspection."

            awareness = build_awareness(
                query=query_text,
                mode=conv_mode,
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                has_image=True,
                support_assessment=support_assessment,
                recent_history=recent_history
            )
            task, stage = infer_task_and_stage(query_text, mode=conv_mode, is_coding=coding_required, has_image=True)
            _apply_temporal_tone(awareness)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="vision_inspection", mode=conv_mode, task=task, stage=stage),
                user_state=UserCognitiveState(emotion=awareness.emotional_state.emotion, intensity=awareness.emotional_state.intensity, confidence=0.9, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.6),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=awareness.recent_topic, **_temporal_context_fields()),
                uncertainty=ConfidenceMetrics(routing_confidence=0.95, emotion_confidence=0.90, memory_relevance=0.85)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type=task_type,
                conversation_mode=conv_mode,
                complexity="medium",
                emotional_importance="low",
                detected_emotion=awareness.emotional_state.emotion,
                emotional_state=awareness.emotional_state,
                support_assessment=support_assessment,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, is_coding=coding_required, has_image=True),
                vision_required=True,
                coding_required=coding_required,
                memory_required=False,
                rag_required=False,
                confidence=0.95,
                support_score=support_assessment.support_score,
                support_level=support_level_str,
                primary_intent=support_assessment.primary_intent,
                secondary_intent=support_assessment.secondary_intent,
                reason=reason,
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # 3. Detect Coding Task vs Conceptual Inquiry
        is_coding = False
        for pat in CODING_PATTERNS:
            if re.search(pat, query_lower):
                is_coding = True
                break

        is_conceptual = any(re.search(pat, query_lower) for pat in CONCEPTUAL_PATTERNS)
        if is_conceptual and not any(kw in query_lower for kw in ["implement", "code", "write", "debug", "fix", "script", "java", "python", "cpp", "endpoint", "traceback"]):
            is_coding = False

        # 4. Detect Memory Requirement
        memory_required = any(re.search(pat, query_lower) for pat in MEMORY_PATTERNS)

        # 5. DECISION HIERARCHY EVALUATION

        # Rank 1: High-Priority Distress / Strong Support Need -> Hermes 2 (Support Mode)
        if (
            support_assessment.support_type == SupportType.HIGH_PRIORITY_DISTRESS or
            (support_assessment.activation_level == HermesActivationLevel.HIGH and support_assessment.support_need >= settings.HERMES_SUPPORT_HIGH_THRESHOLD)
        ):
            selected_model = settings.MODEL_HERMES
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="support",
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                support_assessment=support_assessment,
                recent_history=recent_history
            )
            task, stage = infer_task_and_stage(query_text, mode="support", is_coding=False, has_image=False)
            _apply_temporal_tone(awareness)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="emotional_support", mode="support", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=support_assessment.emotion_intensity, confidence=support_assessment.confidence, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.5),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, **_temporal_context_fields()),
                uncertainty=ConfidenceMetrics(routing_confidence=0.94, emotion_confidence=support_assessment.confidence, memory_relevance=0.80)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="emotional_support",
                conversation_mode="support",
                complexity="medium",
                emotional_importance="high",
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                support_assessment=support_assessment,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="emotional_support", is_coding=False, has_image=False),
                vision_required=False,
                coding_required=False,
                memory_required=memory_required,
                rag_required=False,
                confidence=0.94,
                support_score=support_assessment.support_score,
                support_level="high",
                primary_intent=support_assessment.primary_intent,
                secondary_intent=support_assessment.secondary_intent,
                reason=support_assessment.routing_reason or "High emotional support need identified; routing to Hermes 2 for empathetic and reflective presence.",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Rank 2: Mixed Support + Practical Request
        if support_assessment.support_type == SupportType.MIXED_SUPPORT_PRACTICAL:
            # If support need is dominant (>= 0.60): Hermes provides empathetic opening and then addresses practical issue
            if support_assessment.support_need >= 0.60:
                selected_model = settings.MODEL_HERMES
                conv_mode = "support"
                task_type = "mixed_support_practical"
                reason = "Mixed emotional + practical request; Hermes 2 validates user experience before providing practical direction."
            else:
                # Practical problem dominates, but emotional context is preserved in ResponsePlan
                if is_coding:
                    selected_model = settings.MODEL_CODER
                    conv_mode = "builder"
                    task_type = "coding_task"
                else:
                    selected_model = settings.MODEL_QWEN3
                    conv_mode = "thinking"
                    task_type = "general_reasoning"
                reason = "Practical problem with emotional context; specialist model handles solution while acknowledging emotional state."

            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode=conv_mode,
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                has_code=is_coding,
                support_assessment=support_assessment,
                recent_history=recent_history
            )
            task, stage = infer_task_and_stage(query_text, mode=conv_mode, is_coding=is_coding, has_image=False)
            _apply_temporal_tone(awareness)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic=awareness.current_project or "mixed_task", mode=conv_mode, task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=support_assessment.emotion_intensity, confidence=support_assessment.confidence, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.6),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, **_temporal_context_fields()),
                uncertainty=ConfidenceMetrics(routing_confidence=0.91, emotion_confidence=support_assessment.confidence, memory_relevance=0.85)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type=task_type,
                conversation_mode=conv_mode,
                complexity="medium",
                emotional_importance="medium",
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                support_assessment=support_assessment,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type=task_type, is_coding=is_coding, has_image=False),
                vision_required=False,
                coding_required=is_coding,
                memory_required=memory_required,
                rag_required=False,
                confidence=0.91,
                support_score=support_assessment.support_score,
                support_level=support_level_str,
                primary_intent=support_assessment.primary_intent,
                secondary_intent=support_assessment.secondary_intent,
                reason=reason,
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Rank 3: Moderate Emotional Support Need -> Hermes 2 (Support Mode)
        if (
            support_assessment.activation_level == HermesActivationLevel.MODERATE and
            not is_coding and
            not is_conceptual and
            support_assessment.solution_readiness < 0.60
        ):
            selected_model = settings.MODEL_HERMES
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="support",
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                support_assessment=support_assessment,
                recent_history=recent_history
            )
            task, stage = infer_task_and_stage(query_text, mode="support", is_coding=False, has_image=False)
            _apply_temporal_tone(awareness)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="emotional_support", mode="support", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=support_assessment.emotion_intensity, confidence=support_assessment.confidence, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.5),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, **_temporal_context_fields()),
                uncertainty=ConfidenceMetrics(routing_confidence=0.88, emotion_confidence=support_assessment.confidence, memory_relevance=0.80)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="emotional_support",
                conversation_mode="support",
                complexity="medium",
                emotional_importance="medium",
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                support_assessment=support_assessment,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="emotional_support", is_coding=False, has_image=False),
                vision_required=False,
                coding_required=False,
                memory_required=memory_required,
                rag_required=False,
                confidence=0.88,
                support_score=support_assessment.support_score,
                support_level="moderate",
                primary_intent=support_assessment.primary_intent,
                secondary_intent=support_assessment.secondary_intent,
                reason="Moderate emotional support need identified; Hermes provides validating and empathetic presence.",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Rank 4: Coding Requirement -> Builder Mode (Qwen 2.5 Coder)
        if is_coding:
            selected_model = settings.MODEL_CODER
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="builder",
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                has_code=True,
                support_assessment=support_assessment,
                recent_history=recent_history
            )
            task, stage = infer_task_and_stage(query_text, mode="builder", is_coding=True, has_image=False)
            _apply_temporal_tone(awareness)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic=awareness.current_project or "coding", mode="builder", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=support_assessment.emotion_intensity, confidence=support_assessment.confidence, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.6),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, consecutive_frustrations=awareness.consecutive_frustrations, **_temporal_context_fields()),
                uncertainty=ConfidenceMetrics(routing_confidence=0.92, emotion_confidence=support_assessment.confidence, memory_relevance=0.85)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="coding_task",
                conversation_mode="builder",
                complexity="high",
                emotional_importance=emotional_importance,
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                support_assessment=support_assessment,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="coding_task", is_coding=True, has_image=False),
                vision_required=False,
                coding_required=True,
                memory_required=memory_required,
                rag_required=False,
                confidence=0.92,
                support_score=support_assessment.support_score,
                support_level=support_level_str,
                primary_intent="coding_task",
                secondary_intent=support_assessment.secondary_intent,
                reason="Primary task requires software engineering, debugging, or implementation (Builder Mode).",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Rank 5: Low Complexity / Simple Chat / Casual Mode (Phi-3)
        words = re.findall(r"\b\w+\b", query_lower)
        is_greeting = query_lower in GREETING_KEYWORDS or any(query_lower.startswith(g) for g in ["hi", "hello", "hey", "good morning", "good evening", "good night", "thanks", "thank you", "byebye", "bye", "status", "ping"])
        is_simple_banter = is_greeting or (len(words) <= 5 and not is_conceptual and not any(kw in query_lower for kw in ["approach", "architecture", "design", "think", "explain", "why", "how", "reason", "system"]))

        # Model stability: if previously in thinking/builder mode and query is not simple greeting, avoid dropping to phi3
        if previous_model in [settings.MODEL_QWEN3, settings.MODEL_CODER] and not is_greeting and not is_simple_banter:
            is_simple_banter = False

        if is_simple_banter and not memory_required and emotional_importance == "low":
            selected_model = settings.MODEL_PHI3
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="casual",
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                support_assessment=support_assessment,
                recent_history=recent_history
            )
            task, stage = infer_task_and_stage(query_text, mode="casual", is_coding=False, has_image=False)
            _apply_temporal_tone(awareness)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="casual_banter", mode="casual", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=support_assessment.emotion_intensity, confidence=support_assessment.confidence, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.3),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, **_temporal_context_fields()),
                uncertainty=ConfidenceMetrics(routing_confidence=0.90, emotion_confidence=support_assessment.confidence, memory_relevance=0.75)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="simple_chat",
                conversation_mode="casual",
                complexity="low",
                emotional_importance="low",
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                support_assessment=support_assessment,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="simple_chat", is_coding=False, has_image=False),
                vision_required=False,
                coding_required=False,
                memory_required=False,
                rag_required=False,
                confidence=0.90,
                support_score=support_assessment.support_score,
                support_level=support_level_str,
                primary_intent="casual_chat",
                secondary_intent=None,
                reason="Fast everyday conversational banter routed via lightweight Phi-3 (Casual Mode).",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Rank 6: Deep Reasoning / Thinking Mode (Qwen3 8B Fallback)
        complexity_level = "high" if len(words) > 25 or "?" in query_text else "medium"
        selected_model = settings.MODEL_QWEN3
        if memory_data:
            selected_model = apply_learned_policies(query_text, selected_model, memory_data)

        awareness = build_awareness(
            query=query_text,
            mode="thinking",
            selected_model=selected_model,
            previous_awareness=previous_awareness,
            support_assessment=support_assessment,
            recent_history=recent_history
        )
        task, stage = infer_task_and_stage(query_text, mode="thinking", is_coding=False, has_image=False)
        _apply_temporal_tone(awareness)
        cognitive_state = SakiCognitiveState(
            conversation=ConversationState(topic="reasoning_and_learning", mode="thinking", task=task, stage=stage),
            user_state=UserCognitiveState(emotion=detected_emotion, intensity=support_assessment.emotion_intensity, confidence=support_assessment.confidence, needs=awareness.emotional_state.needs),
            saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.7),
            context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, **_temporal_context_fields()),
            uncertainty=ConfidenceMetrics(routing_confidence=0.88, emotion_confidence=support_assessment.confidence, memory_relevance=0.88)
        )
        return RoutingDecision(
            selected_model=selected_model,
            task_type="general_reasoning",
            conversation_mode="thinking",
            complexity=complexity_level,
            emotional_importance=emotional_importance,
            detected_emotion=detected_emotion,
            emotional_state=awareness.emotional_state,
            support_assessment=support_assessment,
            social_energy=awareness.social_energy,
            awareness=awareness,
            cognitive_state=cognitive_state,
            action_decision=decide_action(query_text, attachments, memory_data, task_type="general_reasoning", is_coding=False, has_image=False),
            vision_required=False,
            coding_required=False,
            memory_required=memory_required,
            rag_required=False,
            confidence=0.88,
            support_score=support_assessment.support_score,
            support_level=support_level_str,
            primary_intent=support_assessment.primary_intent,
            secondary_intent=support_assessment.secondary_intent,
            reason="Analytical reasoning or conceptual inquiry routed to Qwen3 8B (Thinking Mode).",
            should_switch_model=(previous_model != selected_model) if previous_model else False,
            should_stop_after_response=True,
            keep_loaded=False
        )

    # Alias for conversational brain routing
    route_request = classify_request

