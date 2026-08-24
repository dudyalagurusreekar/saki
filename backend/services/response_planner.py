"""
Saki Response Planner
Generates a pre-generation strategy blueprint before model invocation, ensuring
all models adhere to Saki's unified goal, tone, depth, and emotional strategy.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.core.saki_state import SakiCognitiveState
from backend.services.emotional_support_service import SupportAssessment, SupportType


class ResponseType(str, Enum):
    PURE_EMOTIONAL = "pure_emotional"
    PRACTICAL_WITH_EMOTION = "practical_with_emotion"
    MIXED_EMOTIONAL_PRACTICAL = "mixed_emotional_practical"
    NORMAL_CONVERSATION = "normal_conversation"
    TECHNICAL = "technical"
    COMPLEX_REASONING = "complex_reasoning"


class AdaptiveLength(str, Enum):
    ULTRA_CONCISE = "ultra_concise"      # 1-2 sentences / <= 25 words (greetings, simple acknowledgements)
    BALANCED = "balanced"                # 1-2 short paragraphs (standard dialogue)
    DEEP_STRUCTURED = "deep_structured"  # Full technical breakdown, code snippets, architecture


class ResponsePlan(BaseModel):
    goal: str = Field(description="Core objective of the response")
    response_type: ResponseType = Field(default=ResponseType.NORMAL_CONVERSATION, description="Primary response category")
    adaptive_length: AdaptiveLength = Field(default=AdaptiveLength.BALANCED, description="Target conversational length")
    tone: str = Field(description="Target tone: warm_collaborative, calm_focused, playful_banter, empathetic_gentle, structured_educational, validating_supportive")
    depth: str = Field(default="moderate", description="concise, moderate, high")
    acknowledge_emotion: bool = Field(default=False, description="Whether to acknowledge emotion explicitly")
    use_humor: bool = Field(default=False, description="Whether light humor/wit is appropriate")
    ask_question: bool = Field(default=False, description="Whether to include a follow-up question")
    technical_detail: str = Field(default="medium", description="none, low, medium, high")
    validate_before_solve: bool = Field(default=False, description="Whether to validate emotional experience before providing any solutions")
    directive_prompt: str = Field(default="", description="Instructional prompt block injected into the LLM")


def _is_ultra_concise_query(clean_query: str) -> bool:
    """Detects simple greetings, acknowledgements, and single confirmations that require ultra-concise replies."""
    q = clean_query.strip().lower()
    
    # Common greetings
    greetings = {
        "good morning", "morning", "good morning saki", "morning saki",
        "good afternoon", "good evening", "good night", "hey", "hey saki",
        "hello", "hello saki", "hi", "hi saki", "yo", "sup", "what's up", "whats up"
    }
    if q in greetings or any(q == g for g in greetings):
        return True

    # Common short conversational acknowledgements / check-ins
    acknowledgements = {
        "did you understand", "did you understand?", "did you get it", "did you get it?",
        "got it?", "understand?", "you there?", "are you there?", "can you hear me?",
        "thanks", "thank you", "thanks saki", "thank you saki", "ok", "okay", "cool",
        "great", "awesome", "perfect", "sounds good", "got you", "i see"
    }
    if q in acknowledgements or any(q == a for a in acknowledgements):
        return True

    # Single-word or 2-word casual checks
    words = q.split()
    if len(words) <= 2 and any(w in ["morning", "hello", "hi", "hey", "thanks", "ok", "cool"] for w in words):
        return True

    return False


def plan_response(
    state: SakiCognitiveState,
    query: str,
    user_preferences: Optional[List[str]] = None,
    support_assessment: Optional[SupportAssessment] = None
) -> ResponsePlan:
    """
    Creates a strategic response plan based on Cognitive State, task, emotion, support assessment, and user preferences.
    """
    clean_q = query.strip()
    task = state.conversation.task
    mode = state.conversation.mode
    emotion = state.user_state.emotion
    intensity = state.user_state.intensity
    frustrations = state.context.consecutive_frustrations
    prefs = [p.lower() for p in (user_preferences or [])]

    # Check for ultra-concise conversational triggers
    is_ultra_concise = _is_ultra_concise_query(clean_q)
    prefers_concise = any("concise" in p or "short" in p for p in prefs)

    # 1. High Emotional Support / Loneliness / Overwhelm / Burnout (Support Mode / Hermes 2)
    if mode == "support" or task in ["emotional_support", "emotional_venting"]:
        cause = support_assessment.cause if support_assessment else "personal emotional experience"
        sol_ready = support_assessment.solution_readiness if support_assessment else 0.20

        if sol_ready < 0.35:
            directive = (
                "Response Strategy (Pure Emotional Support & Validation):\n"
                f"- Understand what happened: Acknowledge the actual context ('{cause}') specifically with genuine presence.\n"
                "- Validate Before Solve: Show the user that you hear why this is exhausting, frustrating, or disappointing.\n"
                "- DO NOT jump into unsolicited advice, step-by-step checklists, or generic self-help worksheets.\n"
                "- NO robotic cliches ('I apologize', 'As an AI', 'I understand this is difficult', 'Here are some tips').\n"
                "- Maintain healthy boundaries: Be a grounded, attentive companion who encourages self-agency.\n"
                "- Match the user's conversational intensity with warmth and presence. Ask at most one gentle follow-up."
            )
            return ResponsePlan(
                goal="provide_authentic_emotional_validation_and_presence",
                response_type=ResponseType.PURE_EMOTIONAL,
                adaptive_length=AdaptiveLength.BALANCED,
                tone="empathetic_gentle",
                depth="moderate",
                acknowledge_emotion=True,
                use_humor=False,
                ask_question=True,
                technical_detail="none",
                validate_before_solve=True,
                directive_prompt=directive
            )
        else:
            directive = (
                "Response Strategy (Empathetic Presence with Solution Openness):\n"
                f"- Acknowledge the user's feelings about '{cause}' first in 1-2 warm, grounded sentences.\n"
                "- Offer a clear, thoughtful perspective or natural next step only after validating.\n"
                "- Keep suggestions focused (1-2 practical thoughts) rather than a wall of generic advice."
            )
            return ResponsePlan(
                goal="validate_feelings_then_provide_practical_direction",
                response_type=ResponseType.MIXED_EMOTIONAL_PRACTICAL,
                adaptive_length=AdaptiveLength.BALANCED,
                tone="validating_supportive",
                depth="moderate",
                acknowledge_emotion=True,
                use_humor=False,
                ask_question=False,
                technical_detail="low",
                validate_before_solve=True,
                directive_prompt=directive
            )

    # 2. Mixed Support + Practical (Hermes or Coder/Qwen with empathetic opening)
    if task == "mixed_support_practical" or (support_assessment and support_assessment.support_type == SupportType.MIXED_SUPPORT_PRACTICAL):
        return ResponsePlan(
            goal="validate_feelings_then_provide_practical_direction",
            response_type=ResponseType.MIXED_EMOTIONAL_PRACTICAL,
            adaptive_length=AdaptiveLength.BALANCED,
            tone="validating_supportive",
            depth="moderate",
            acknowledge_emotion=True,
            use_humor=False,
            ask_question=False,
            technical_detail="medium",
            validate_before_solve=True,
            directive_prompt=(
                "Response Strategy (Validate First, Then Guide):\n"
                "- First, recognize the user's disappointment/frustration naturally in 1 sentence.\n"
                "- Then transition smoothly into the practical direction or technical solution.\n"
                "- Keep the solution clear, structured, and immediately actionable."
            )
        )

    # 3. Practical Request with Emotion (e.g., Frustrated with bug -> Builder Mode)
    if (support_assessment and support_assessment.support_type == SupportType.PRACTICAL_WITH_EMOTION) or task == "bug_fixing":
        return ResponsePlan(
            goal="isolate_bug_calmly_and_provide_fix",
            response_type=ResponseType.PRACTICAL_WITH_EMOTION,
            adaptive_length=AdaptiveLength.BALANCED,
            tone="calm_focused",
            depth="moderate",
            acknowledge_emotion=True,
            use_humor=False,
            ask_question=False,
            technical_detail="high",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy:\n"
                "- Acknowledge the friction/frustration in 1 natural opening sentence without drama (e.g. 'That bug is stubborn. Let\\'s isolate it step-by-step.').\n"
                "- Deliver the clean, direct fix, code snippet, or diagnostic steps immediately.\n"
                "- Keep technical explanations production-ready and concise."
            )
        )

    # 4. Celebration / Breakthrough
    if emotion == "celebrating":
        return ResponsePlan(
            goal="celebrate_breakthrough_with_enthusiasm",
            response_type=ResponseType.NORMAL_CONVERSATION,
            adaptive_length=AdaptiveLength.ULTRA_CONCISE if len(clean_q.split()) <= 6 else AdaptiveLength.BALANCED,
            tone="playful_banter",
            depth="concise",
            acknowledge_emotion=True,
            use_humor=True,
            ask_question=False,
            technical_detail="none",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy:\n"
                "- Celebrate the breakthrough with genuine hype and shared excitement.\n"
                "- Keep it brief, natural, and energetic."
            )
        )

    # 5. Technical / Coding Request
    if task in ["coding_task", "software_engineering", "technical_explanation"] or mode == "builder":
        return ResponsePlan(
            goal="debug_and_resolve_issue",
            response_type=ResponseType.TECHNICAL,
            adaptive_length=AdaptiveLength.DEEP_STRUCTURED if len(clean_q.split()) > 15 else AdaptiveLength.BALANCED,
            tone="warm_collaborative",
            depth="high",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=False,
            technical_detail="high",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy:\n"
                "- Deliver precise code and technical diagnostics directly.\n"
                "- Maintain a collaborative, sharp pair-programming voice."
            )
        )

    # 5. Architecture Design & Planning (Thinking / Builder Mode)
    if task == "architecture_design":
        return ResponsePlan(
            goal="structure_robust_architecture",
            response_type=ResponseType.COMPLEX_REASONING,
            adaptive_length=AdaptiveLength.DEEP_STRUCTURED,
            tone="warm_collaborative",
            depth="high",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=True,
            technical_detail="high",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy:\n"
                "- Break down the architecture clearly with modular components.\n"
                "- Highlight tradeoffs, data flows, and concrete implementation steps."
            )
        )

    # 6. Concept Learning / Explanation (Thinking Mode)
    if task == "concept_learning" or mode == "thinking":
        return ResponsePlan(
            goal="explain_concept_clearly_and_intuitively",
            response_type=ResponseType.COMPLEX_REASONING,
            adaptive_length=AdaptiveLength.DEEP_STRUCTURED if len(clean_q.split()) > 10 else AdaptiveLength.BALANCED,
            tone="structured_educational",
            depth="high" if len(clean_q.split()) > 10 else "moderate",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=False,
            technical_detail="medium",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy:\n"
                "- Explain using intuitive analogies and practical real-world examples.\n"
                "- Structure key points with clarity and conciseness."
            )
        )

    # 7. Vision Analysis (Vision Mode)
    if mode == "vision" or task == "vision_analysis":
        return ResponsePlan(
            goal="analyze_visual_layout_and_elements",
            response_type=ResponseType.TECHNICAL,
            adaptive_length=AdaptiveLength.BALANCED,
            tone="warm_collaborative",
            depth="moderate",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=False,
            technical_detail="medium",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy:\n"
                "- Clearly identify key visual elements, text OCR, layout structure, or errors.\n"
                "- Present findings concisely and accurately."
            )
        )

    # 8. Greetings & Ultra-Concise Checks
    if is_ultra_concise:
        return ResponsePlan(
            goal="natural_ultra_concise_acknowledgement",
            response_type=ResponseType.NORMAL_CONVERSATION,
            adaptive_length=AdaptiveLength.ULTRA_CONCISE,
            tone="playful_banter" if mode == "casual" else "warm_collaborative",
            depth="concise",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=False,
            technical_detail="none",
            validate_before_solve=False,
            directive_prompt=(
                "Response Strategy (Ultra-Concise Greeting / Acknowledgement):\n"
                "- Keep response extremely concise (1 single sentence or short phrase).\n"
                "- Example for 'Morning': 'Morning! 😊' or 'Good morning! Ready when you are.'\n"
                "- Example for 'Did you understand?': 'Yeah, I got you.'\n"
                "- Do NOT write long introductory paragraphs, lists, or generic pleasantries."
            )
        )

    # 9. Casual Everyday Banter (Casual Mode)
    return ResponsePlan(
        goal="lively_friendly_banter",
        response_type=ResponseType.NORMAL_CONVERSATION,
        adaptive_length=AdaptiveLength.ULTRA_CONCISE if prefers_concise else AdaptiveLength.BALANCED,
        tone="playful_banter",
        depth="concise",
        acknowledge_emotion=False,
        use_humor=True,
        ask_question=False,
        technical_detail="none",
        validate_before_solve=False,
        directive_prompt=(
            "Response Strategy:\n"
            "- Keep response concise (1-2 sentences), lively, warm, and natural."
        )
    )

