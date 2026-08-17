"""
Saki Response Planner
Generates a pre-generation strategy blueprint before model invocation, ensuring
all models adhere to Saki's unified goal, tone, depth, and emotional strategy.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.core.saki_state import SakiCognitiveState


class ResponsePlan(BaseModel):
    goal: str = Field(description="Core objective of the response")
    tone: str = Field(description="Target tone: warm_collaborative, calm_focused, playful_banter, empathetic_gentle, structured_educational")
    depth: str = Field(default="moderate", description="concise, moderate, high")
    acknowledge_emotion: bool = Field(default=False, description="Whether to acknowledge emotion explicitly")
    use_humor: bool = Field(default=False, description="Whether light humor/wit is appropriate")
    ask_question: bool = Field(default=False, description="Whether to include a follow-up question")
    technical_detail: str = Field(default="medium", description="none, low, medium, high")
    directive_prompt: str = Field(default="", description="Instructional prompt block injected into the LLM")


def plan_response(
    state: SakiCognitiveState,
    query: str,
    user_preferences: Optional[List[str]] = None
) -> ResponsePlan:
    """
    Creates a strategic response plan based on Cognitive State, task, emotion, and preferences.
    """
    task = state.conversation.task
    mode = state.conversation.mode
    emotion = state.user_state.emotion
    intensity = state.user_state.intensity
    frustrations = state.context.consecutive_frustrations
    prefs = [p.lower() for p in (user_preferences or [])]

    # Preference overrides
    prefers_concise = any("concise" in p or "short" in p for p in prefs)
    default_depth = "concise" if prefers_concise or mode == "casual" else ("high" if mode in ["thinking", "builder"] and len(query.split()) > 15 else "moderate")

    # 1. Bug Fixing / Debugging Roadblocks (Builder Mode)
    if task == "bug_fixing":
        if emotion == "frustrated" or frustrations >= 1:
            return ResponsePlan(
                goal="isolate_bug_calmly_and_provide_fix",
                tone="calm_focused",
                depth=default_depth,
                acknowledge_emotion=True,
                use_humor=False,
                ask_question=False,
                technical_detail="high",
                directive_prompt=(
                    "Response Strategy:\n"
                    "- Acknowledge the frustrating bug in 1 natural sentence without dramatic pity (e.g. 'Ahh, that bug again 😭. Don't fight it alone—let's isolate it.').\n"
                    "- Provide the clean, direct fix or debugging steps immediately.\n"
                    "- Keep explanations clear, practical, and production-ready."
                )
            )
        else:
            return ResponsePlan(
                goal="debug_and_resolve_issue",
                tone="warm_collaborative",
                depth=default_depth,
                acknowledge_emotion=False,
                use_humor=True,
                ask_question=False,
                technical_detail="high",
                directive_prompt=(
                    "Response Strategy:\n"
                    "- Deliver precise code and technical diagnostics directly.\n"
                    "- Maintain a collaborative, sharp pair-programming voice."
                )
            )

    # 2. Celebration / Win
    if emotion == "celebrating":
        return ResponsePlan(
            goal="celebrate_breakthrough_with_enthusiasm",
            tone="playful_banter",
            depth="concise",
            acknowledge_emotion=True,
            use_humor=True,
            ask_question=True,
            technical_detail="none",
            directive_prompt=(
                "Response Strategy:\n"
                "- Celebrate the win with genuine hype and excitement ('YES 😂 Finally! That thing was refusing to cooperate.').\n"
                "- Keep it brief, natural, and energetic."
            )
        )

    # 3. Emotional Support / Loneliness / Overwhelm (Support Mode)
    if mode == "support" or task == "emotional_venting":
        return ResponsePlan(
            goal="provide_comfort_validation_and_presence",
            tone="empathetic_gentle",
            depth="moderate",
            acknowledge_emotion=True,
            use_humor=False,
            ask_question=True,
            technical_detail="none",
            directive_prompt=(
                "Response Strategy:\n"
                "- Listen deeply and validate how the user feels before suggesting anything.\n"
                "- Be a warm, grounding presence.\n"
                "- NO robotic phrases ('I apologize', 'As an AI', 'How can I assist you')."
            )
        )

    # 4. Architecture Design & Planning (Thinking / Builder Mode)
    if task == "architecture_design":
        return ResponsePlan(
            goal="structure_robust_architecture",
            tone="warm_collaborative",
            depth="high",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=True,
            technical_detail="high",
            directive_prompt=(
                "Response Strategy:\n"
                "- Break down the architecture clearly with modular components.\n"
                "- Highlight tradeoffs, data flows, and concrete implementation steps."
            )
        )

    # 5. Concept Learning / Explanation (Thinking Mode)
    if task == "concept_learning" or mode == "thinking":
        return ResponsePlan(
            goal="explain_concept_clearly_and_intuitively",
            tone="structured_educational",
            depth=default_depth,
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=False,
            technical_detail="medium",
            directive_prompt=(
                "Response Strategy:\n"
                "- Explain using intuitive analogies and practical real-world examples.\n"
                "- Structure key points with clarity and conciseness."
            )
        )

    # 6. Vision Analysis
    if mode == "vision" or task == "vision_analysis":
        return ResponsePlan(
            goal="analyze_visual_layout_and_elements",
            tone="warm_collaborative",
            depth="moderate",
            acknowledge_emotion=False,
            use_humor=False,
            ask_question=False,
            technical_detail="high",
            directive_prompt=(
                "Response Strategy:\n"
                "- Describe and analyze the image / UI layout accurately and concisely."
            )
        )

    # 7. Default Casual Banter (Casual Mode / Phi-3)
    return ResponsePlan(
        goal="lively_friendly_banter",
        tone="playful_banter",
        depth="concise",
        acknowledge_emotion=False,
        use_humor=True,
        ask_question=False,
        technical_detail="none",
        directive_prompt=(
            "Response Strategy:\n"
            "- Keep response concise (1-3 sentences), warm, and natural.\n"
            "- Speak like a close, witty friend."
        )
    )
