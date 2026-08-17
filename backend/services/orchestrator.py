import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.config import settings
from backend.services.emotional_intelligence import (
    EmotionalState,
    SocialEnergyState,
    SakiAwareness,
    analyze_emotional_state,
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


class RoutingDecision(BaseModel):
    selected_model: str = Field(description="Ollama model tag to execute")
    task_type: str = Field(description="simple_chat, emotional_support, coding_task, vision_analysis, general_reasoning")
    conversation_mode: str = Field(default="casual", description="casual, support, thinking, builder, vision")
    complexity: str = Field(description="low, medium, high, complex")
    emotional_importance: str = Field(description="low, medium, high")
    detected_emotion: str = Field(default="neutral", description="neutral, sad, anxious, frustrated, excited, celebrating, etc.")
    emotional_state: EmotionalState = Field(default_factory=EmotionalState)
    social_energy: SocialEnergyState = Field(default_factory=SocialEnergyState)
    awareness: Optional[SakiAwareness] = None
    cognitive_state: Optional[SakiCognitiveState] = None
    action_decision: Optional[ActionDecision] = None
    vision_required: bool = Field(default=False)
    coding_required: bool = Field(default=False)
    memory_required: bool = Field(default=False)
    rag_required: bool = Field(default=False)
    confidence: float = Field(description="Routing confidence score 0.0 to 1.0")
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

# Emotional triggers (pure relational emotional requests)
EMOTIONAL_SUPPORT_PATTERNS = [
    (r"\b(feel|feeling|felt)\s+(bad|sad|terrible|horrible|lonely|anxious|depressed|down|awful|hopeless)\b", "sad", "high"),
    (r"\b(don't know what|dont know what)\s+i'm doing\b", "anxious", "high"),
    (r"\b(had a|having a)\s+(terrible|bad|horrible|rough|hard)\s+(day|time|week)\b", "sad", "high"),
    (r"\b(excited|happy|thrilled|great news)\b", "excited", "medium"),
    (r"\b(need someone to listen|can i talk to you|i feel lonely|help me calm down)\b", "sad", "high"),
    (r"\b(stressed|overwhelmed|burnt out|burnout)\b", "overwhelmed", "high"),
    (r"\b(frustrated|annoyed|angry)\s+with\s+(myself|life|everything)\b", "frustrated", "high")
]

# Code & programming indicators
CODING_PATTERNS = [
    r"```[a-zA-Z]*",
    r"\b(traceback|stack trace|exception|syntaxerror|nullpointerexception|typeerror|valueerror|indexerror)\b",
    r"\b(fix this|debug this|refactor|write a function|create a component|implement|script|fastapi|react|next\.js|python|java|typescript|javascript|dockerfile|sql query)\b",
    r"\b(endpoint failing|code error|bug in|compilation error|npm error|pip error|500 internal server error)\b"
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
    and synthesizes the unified Saki Cognitive State.
    """

    @staticmethod
    def classify_request(
        query: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        previous_model: Optional[str] = None,
        previous_awareness: Optional[SakiAwareness] = None,
        memory_data: Optional[Dict[str, Any]] = None,
        is_voice_mode: bool = False
    ) -> RoutingDecision:
        query_text = (query or "").strip()
        query_lower = query_text.lower()
        attachments = attachments or []

        # 1. Detect Vision Requirement (Mode: vision -> Gemma 3)
        has_image_attachment = any(
            att.get("type") in ["image", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"] 
            or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            for att in attachments
        )
        vision_keywords = ["screenshot", "this image", "in this picture", "this diagram", "read text from photo", "visual layout"]
        has_vision_keyword = any(kw in query_lower for kw in vision_keywords)
        
        vision_required = has_image_attachment or (has_vision_keyword and len(attachments) > 0)

        if vision_required:
            awareness = build_awareness(
                query=query_text,
                mode="vision",
                selected_model=settings.MODEL_GEMMA,
                previous_awareness=previous_awareness,
                has_image=True
            )
            task, stage = infer_task_and_stage(query_text, mode="vision", is_coding=False, has_image=True)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="vision_inspection", mode="vision", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=awareness.emotional_state.emotion, intensity=awareness.emotional_state.intensity, confidence=0.9, needs=awareness.emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.6),
                context=ContextState(active_project=awareness.current_project, last_model=settings.MODEL_GEMMA, recent_topic=awareness.recent_topic),
                uncertainty=ConfidenceMetrics(routing_confidence=0.95, emotion_confidence=0.90, memory_relevance=0.85)
            )
            return RoutingDecision(
                selected_model=settings.MODEL_GEMMA,
                task_type="vision_analysis",
                conversation_mode="vision",
                complexity="medium",
                emotional_importance="low",
                detected_emotion=awareness.emotional_state.emotion,
                emotional_state=awareness.emotional_state,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, is_coding=False, has_image=True),
                vision_required=True,
                coding_required=False,
                memory_required=False,
                rag_required=False,
                confidence=0.95,
                reason="Request requires visual analysis model (Gemma 3) for image or screenshot inspection.",
                should_switch_model=(previous_model != settings.MODEL_GEMMA) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # 2. Detect Coding Task vs Conceptual Inquiry
        is_coding = False
        for pat in CODING_PATTERNS:
            if re.search(pat, query_lower):
                is_coding = True
                break

        # Check if request is purely conceptual (e.g., "What is a linked list?")
        is_conceptual = any(re.search(pat, query_lower) for pat in CONCEPTUAL_PATTERNS)
        if is_conceptual and not any(kw in query_lower for kw in ["implement", "code", "write", "debug", "fix", "script", "java", "python", "cpp", "endpoint", "traceback"]):
            is_coding = False

        # 3. Detect Emotional State & User Needs
        emotional_state, new_frustrations = analyze_emotional_state(
            query_text,
            consecutive_frustrations=previous_awareness.consecutive_frustrations if previous_awareness else 0
        )
        detected_emotion = emotional_state.emotion
        emotional_importance = "high" if emotional_state.intensity >= 0.75 and detected_emotion in ["sad", "anxious", "overwhelmed"] else ("medium" if emotional_state.intensity >= 0.6 else "low")
        is_pure_emotional_request = (detected_emotion in ["sad", "overwhelmed", "anxious"]) and not is_coding and not is_conceptual

        # 4. Detect Memory Requirement
        memory_required = any(re.search(pat, query_lower) for pat in MEMORY_PATTERNS)

        # 5. Decoupled Routing Precedence

        # Scenario A: Coding Required -> Builder Mode (Qwen2.5-Coder)
        # Even if user is frustrated, dominant task capability is coding!
        if is_coding:
            selected_model = settings.MODEL_CODER
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="builder",
                selected_model=selected_model,
                previous_awareness=previous_awareness,
                has_code=True
            )
            task, stage = infer_task_and_stage(query_text, mode="builder", is_coding=True, has_image=False)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic=awareness.current_project or "coding", mode="builder", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=emotional_state.intensity, confidence=emotional_state.confidence, needs=emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.6),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task, consecutive_frustrations=new_frustrations),
                uncertainty=ConfidenceMetrics(routing_confidence=0.92, emotion_confidence=emotional_state.confidence, memory_relevance=0.85)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="coding_task",
                conversation_mode="builder",
                complexity="high",
                emotional_importance=emotional_importance,
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="coding_task", is_coding=True, has_image=False),
                vision_required=False,
                coding_required=True,
                memory_required=memory_required,
                rag_required=False,
                confidence=0.92,
                reason="Primary task requires engineering, debugging, or implementation (Builder Mode).",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Scenario B: Pure Emotional Support Request -> Support Mode (Hermes 2)
        if emotional_importance == "high" and is_pure_emotional_request:
            selected_model = settings.MODEL_HERMES
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="support",
                selected_model=selected_model,
                previous_awareness=previous_awareness
            )
            task, stage = infer_task_and_stage(query_text, mode="support", is_coding=False, has_image=False)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="emotional_support", mode="support", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=emotional_state.intensity, confidence=emotional_state.confidence, needs=emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.5),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task),
                uncertainty=ConfidenceMetrics(routing_confidence=0.94, emotion_confidence=emotional_state.confidence, memory_relevance=0.80)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="emotional_support",
                conversation_mode="support",
                complexity="medium",
                emotional_importance="high",
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="emotional_support", is_coding=False, has_image=False),
                vision_required=False,
                coding_required=False,
                memory_required=memory_required,
                rag_required=False,
                confidence=0.94,
                reason="User's emotional state calls for empathetic and reflective presence (Support Mode).",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Scenario C: Low Complexity / Simple Chat / Casual Mode (Phi-3)
        words = re.findall(r"\b\w+\b", query_lower)
        is_greeting = query_lower in GREETING_KEYWORDS or (len(words) <= 3 and any(w in GREETING_KEYWORDS for w in words))
        is_simple_question = len(words) <= 7 and not memory_required and emotional_importance == "low"

        if (is_greeting or (is_simple_question and not is_conceptual) or is_voice_mode) and len(words) < 15 and not memory_required:
            selected_model = settings.MODEL_PHI3
            if memory_data:
                selected_model = apply_learned_policies(query_text, selected_model, memory_data)

            awareness = build_awareness(
                query=query_text,
                mode="casual",
                selected_model=selected_model,
                previous_awareness=previous_awareness
            )
            task, stage = infer_task_and_stage(query_text, mode="casual", is_coding=False, has_image=False)
            cognitive_state = SakiCognitiveState(
                conversation=ConversationState(topic="casual_banter", mode="casual", task=task, stage=stage),
                user_state=UserCognitiveState(emotion=detected_emotion, intensity=emotional_state.intensity, confidence=emotional_state.confidence, needs=emotional_state.needs),
                saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.3),
                context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task),
                uncertainty=ConfidenceMetrics(routing_confidence=0.90, emotion_confidence=emotional_state.confidence, memory_relevance=0.75)
            )
            return RoutingDecision(
                selected_model=selected_model,
                task_type="simple_chat",
                conversation_mode="casual",
                complexity="low",
                emotional_importance="low",
                detected_emotion=detected_emotion,
                emotional_state=awareness.emotional_state,
                social_energy=awareness.social_energy,
                awareness=awareness,
                cognitive_state=cognitive_state,
                action_decision=decide_action(query_text, attachments, memory_data, task_type="simple_chat", is_coding=False, has_image=False),
                vision_required=False,
                coding_required=False,
                memory_required=False,
                rag_required=False,
                confidence=0.90,
                reason="Fast everyday conversational banter routed via lightweight Phi-3 (Casual Mode).",
                should_switch_model=(previous_model != selected_model) if previous_model else False,
                should_stop_after_response=True,
                keep_loaded=False
            )

        # Scenario D: Deep Reasoning / Thinking Mode (Qwen3 8B Fallback)
        complexity_level = "high" if len(words) > 25 or "?" in query_text else "medium"
        selected_model = settings.MODEL_QWEN3
        if memory_data:
            selected_model = apply_learned_policies(query_text, selected_model, memory_data)

        awareness = build_awareness(
            query=query_text,
            mode="thinking",
            selected_model=selected_model,
            previous_awareness=previous_awareness
        )
        task, stage = infer_task_and_stage(query_text, mode="thinking", is_coding=False, has_image=False)
        cognitive_state = SakiCognitiveState(
            conversation=ConversationState(topic="reasoning_and_learning", mode="thinking", task=task, stage=stage),
            user_state=UserCognitiveState(emotion=detected_emotion, intensity=emotional_state.intensity, confidence=emotional_state.confidence, needs=emotional_state.needs),
            saki_state=SakiInternalState(warmth=awareness.social_energy.warmth, playfulness=awareness.social_energy.playfulness, seriousness=awareness.social_energy.seriousness, verbosity=0.7),
            context=ContextState(active_project=awareness.current_project, last_model=selected_model, recent_topic=task),
            uncertainty=ConfidenceMetrics(routing_confidence=0.88, emotion_confidence=emotional_state.confidence, memory_relevance=0.88)
        )
        return RoutingDecision(
            selected_model=selected_model,
            task_type="general_reasoning",
            conversation_mode="thinking",
            complexity=complexity_level,
            emotional_importance=emotional_importance,
            detected_emotion=detected_emotion,
            emotional_state=awareness.emotional_state,
            social_energy=awareness.social_energy,
            awareness=awareness,
            cognitive_state=cognitive_state,
            action_decision=decide_action(query_text, attachments, memory_data, task_type="general_reasoning", is_coding=False, has_image=False),
            vision_required=False,
            coding_required=False,
            memory_required=memory_required,
            rag_required=False,
            confidence=0.88,
            reason="Analytical reasoning or learning query routed to Qwen3 8B (Thinking Mode).",
            should_switch_model=(previous_model != selected_model) if previous_model else False,
            should_stop_after_response=True,
            keep_loaded=False
        )
