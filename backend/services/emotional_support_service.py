"""
Saki Emotional Support & Hermes Activation Engine
Advanced multi-signal support assessment, temporal emotional trajectory tracking,
and transparent Hermes activation scoring.
"""

import re
import time
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from backend.core.config import settings


class SupportType(str, Enum):
    EMOTIONAL_EXPRESSION = "EMOTIONAL_EXPRESSION"          # User expressing emotion without seeking support
    EMOTIONAL_SUPPORT_NEED = "EMOTIONAL_SUPPORT_NEED"      # Seeking understanding, validation, reassurance
    PRACTICAL_WITH_EMOTION = "PRACTICAL_WITH_EMOTION"      # Emotional, but primarily practical/technical request
    MIXED_SUPPORT_PRACTICAL = "MIXED_SUPPORT_PRACTICAL"    # Needs emotional acknowledgement first, then practical help
    NORMAL_CONVERSATION = "NORMAL_CONVERSATION"            # Baseline normal interaction
    HIGH_PRIORITY_DISTRESS = "HIGH_PRIORITY_DISTRESS"      # Unusually strong distress, severe burnout, crisis vulnerability


class HermesActivationLevel(str, Enum):
    NONE = "NONE"          # Normal model routing (Phi-3, Coder, Qwen3, Gemma)
    LOW = "LOW"            # Normal model + emotional-awareness guidance in prompt
    MODERATE = "MODERATE"  # Strongly consider Hermes unless specialized capability clearly dominates
    HIGH = "HIGH"          # Select Hermes as primary model unless safety critical requirement blocks it


class SupportAssessment(BaseModel):
    emotion: str = Field(default="neutral", description="Detected primary emotion")
    emotion_intensity: float = Field(default=0.30, description="Emotional intensity 0.0 to 1.0")
    support_need: float = Field(default=0.0, description="True emotional support need score 0.0 to 1.0")
    emotional_importance: float = Field(default=0.0, description="Overall emotional significance in context 0.0 to 1.0")
    implicit_emotion: bool = Field(default=False, description="Whether emotion is communicated implicitly without naming it")
    primary_intent: str = Field(default="general", description="Primary conversational intent")
    secondary_intent: Optional[str] = Field(default=None, description="Secondary intent (e.g., practical problem solving)")
    support_type: SupportType = Field(default=SupportType.NORMAL_CONVERSATION, description="Structured support category")
    cause: str = Field(default="casual conversation", description="Underlying cause or situation")
    solution_readiness: float = Field(default=0.80, description="Readiness for solutions 0.0 (wants to be heard) to 1.0 (wants immediate fix)")
    conversation_shift: str = Field(default="stable", description="stable, escalating_distress, deescalating, shifting_to_practical, shifting_to_personal")
    confidence: float = Field(default=0.85, description="Confidence in assessment 0.0 to 1.0")
    support_score: float = Field(default=0.0, description="Calibrated support score combining multiple signals")
    activation_level: HermesActivationLevel = Field(default=HermesActivationLevel.NONE, description="Hermes activation tier")
    routing_reason: str = Field(default="", description="Diagnostic justification for routing decision")


class EmotionalTurn(BaseModel):
    turn_index: int
    user_message: str
    emotion: str
    intensity: float
    support_need: float
    support_type: str
    topic: str
    timestamp: float = Field(default_factory=time.time)


# ----------------------------------------------------------------------
# MULTI-SIGNAL PATTERNS & HEURISTICS (CONTEXTUAL & IMPLICIT)
# ----------------------------------------------------------------------

EXPLICIT_SUPPORT_PATTERNS = [
    r"\b(need someone to (?:listen|talk to)|can (?:i|we) just talk|(?:feel|feeling) (?:so |very |completely )?lonely|help me calm down)\b",
    r"\b(need (?:some )?(?:comfort|reassurance|encouragement|support)|(?:feel|feeling) (?:so |very |completely )?isolated|(?:haven't|havent) talked to (?:anyone|anybody))\b",
    r"\b(just listen to me|don't give me advice|dont give me advice|i don't want solutions|i dont want solutions|just want to talk)\b",
    r"\b((?:feel|feeling) (?:so |completely |totally )?alone|feel like nobody (?:really )?(?:understands|cares|is there for me)|nobody (?:really )?cares about me)\b",
    r"\b((?:feel|feeling) (?:so )?down|had a (?:really )?(?:rough|terrible|horrible|hard) (?:day|time|week)|feeling overwhelmed and drained)\b",
    # Telugu & Kannada explicit support
    r"(?:నాతో మాట్లాడవా|ఎవరూ లేరు|చాలా ఒంటరిగా ఉంది|ఒంటరిగా అనిపిస్తుంది|ఓదార్పు కావాలి|నా బాధ విను|సహాయం కావాలి)",
    r"(?:నన్ను అర్థం చేసుకునే వారు లేరు|నాకు తోడుగా ఎవరూ లేరు)",
    r"(?:ನನ್ನೊಂದಿಗೆ ಮಾತನಾಡಿ|ಯಾರೂ ಇಲ್ಲ|ತುಂಬಾ ಒಂಟಿತನ ಅನಿಸ್ತಿದೆ|ಬೇಸರವಾಗಿದೆ|ಸಹಾಯ ಬೇಕು|ನನ್ನ ಮಾತು ಕೇಳಿ)"
]

PERSONAL_DISCLOSURE_PATTERNS = [
    r"\b(feel like a (?:total |complete )?failure|i am a failure|i messed up (?:so |really )?badly|hate myself|disappointed in myself)\b",
    r"\b(am i (?:just )?wasting my time|maybe i'm not cut out for this|don't think i can (?:do|handle) this|maybe i am not smart enough)\b",
    r"\b(feel (?:so |completely |totally )?useless|imposter syndrome|don't belong (?:here|at all)|scared (?:about|of) my future|feel hopeless|lost my confidence)\b",
    r"\b(nobody believes in me|let everyone down|ruined everything|everyone else (?:is|seems) so (?:much )?(?:better|further ahead|smarter))\b",
    # Telugu & Kannada personal disclosure
    r"(?:నేను పనికిరాను|నా వల్ల కాదు|నన్ను ఎవరూ నమ్మడం లేదు|నాకు భయంగా ఉంది|ఆత్మవిశ్వాసం కోల్పోయాను)",
    r"(?:ನನ್ನಿಂದ ಆಗ್ತಿಲ್ಲ|ನಾನು ಯಾವುದಕ್ಕೂ ಪ್ರಯೋಜನವಿಲ್ಲ|ನನ್ನ ಮೇಲೆ ನಂಬಿಕೆ ಇಲ್ಲ|ತುಂಬಾ ಹೆದರಿಕೆಯಾಗಿದೆ)"
]

FAILURE_LOSS_CONFLICT_PATTERNS = [
    r"\b(?:worked on this|spent|poured (?:weeks|months|days|hours) (?:into|on))\b.*\b(?:failed|didn't work|didnt work|broken|rejected|useless|ruined|cancelled|shut down)\b",
    r"\b(?:feel|feeling) (?:terrible|awful|horrible|bad) (?:about|from|after)?\s*(?:this|the|my|it|everything|an? (?:project|interview|exam|test|work|job))\b",
    r"\b(rejected my (?:proposal|application|paper|submission)|failed (?:my|the|an) (?:interview|exam|test|presentation|audition|submission)|didn't pass|didnt pass|got rejected (?:by|from)|didn't get the job|didnt get the job)\b",
    r"\b(everything (?:is|seems to be)?\s*(?:failing|broken|falling apart)|everything i (?:try|do) fails|all that work for nothing|back to square one)\b",
    r"\b(i failed (?:my|the|an|at)?|failed at (?:my|the))\b",
    r"\b(broke up with|fight with my (?:friend|partner|parents|boss)|took credit for my (?:work|presentation|project)|betrayed (?:me|my trust)|lost my job|heartbroken|completely lost)\b",
    r"\b(?:they just (?:cancelled|shut down|scrapped|killed) (?:the|my|our) (?:project|work|startup))\b",
    # Telugu & Kannada failure / loss / conflict
    r"(?:ఇంటర్వ్యూ పోయింది|ఇంటర్వ్యూ ఫెయిల్ అయింది|ప్రాజెక్ట్ ఫెయిల్ అయింది|ప్రాజెక్ట్ క్యాన్సల్ చేశారు|జాబ్ రాలేదు|రిజెక్ట్ చేశారు|చాలా బాధగా ఉంది)",
    r"(?:ఇంటర్వ్యూ ఫేల్ అయింది|ప్రాజెక్ట్ ఆగిపోయింది|అంతా నాశనం అయింది)",
    r"(?:ಇಂಟರ್ವ್ಯೂ ಫೇಲ್ ಆಯ್ತು|ಪ್ರಾಜೆಕ್ಟ್ ಹಾಳಾಯ್ತು|ಕೆಲಸ ಸಿಗಲಿಲ್ಲ|ರಿಜೆಕ್ಟ್ ಮಾಡಿದರು|ತುಂಬಾ ಬೇಸರವಾಗಿದೆ|ಎಲ್ಲಾ ವ್ಯರ್ಥವಾಯಿತು)"
]

IMPLICIT_EXHAUSTION_PATTERNS = [
    r"\b(can't (?:take|do|handle) this anymore|cant (?:take|do|handle) this anymore|feel like giving up|i give up|so done with everything)\b",
    r"\b(drowning in (?:work|pressure|stress)|burn(?:ed|t)? out|burnout is real|brain is (?:fried|dead))\b",
    r"\b((?:i am|i'm|im|feel|feeling)?\s*(?:so |completely |totally |really )?(?:exhausted|overwhelmed|burned out|drained)|exhausted today|hard day|had a really hard day)\b",
    r"\b(what's the point|whats the point|why do i even try|exhausted from trying|no energy left)\b",
    # Telugu & Kannada exhaustion
    r"(?:చాలా అలసిపోయాను|భరించలేకపోతున్నాను|మొత్తం విసిగిపోయాను|ఓపిక లేదు|చేయలేకపోతున్నాను)",
    r"(?:ತುಂಬಾ ಸುಸ್ತಾಗಿದೆ|ತಡೆದುಕೊಳ್ಳಲು ಆಗ್ತಿಲ್ಲ|ಸಾಕಾಗಿದೆ|ಮನಸ್ಸಿಗೆ ನೆಮ್ಮದಿ ಇಲ್ಲ)"
]

DISTRESS_PATTERNS = [
    r"\b(panic attack|cant breathe|can't breathe|having a breakdown|severe anxiety|depressed|crying|crying right now|burst into tears|in tears)\b",
    r"\b(terrified|overwhelmed to tears|heart is pounding|chest feels tight|hopeless|feeling hopeless|burned out and crying)\b",
    # Telugu & Kannada acute distress
    r"(?:ఊపిరి ఆడట్లేదు|ఏడుపు వస్తుంది|చాలా భయంగా ఉంది|గుండె వేగంగా కొట్టుకుంటోంది)",
    r"(?:ಉಸಿರಾಟ ಕಷ್ಟವಾಗ್ತಿದೆ|ಅಳು ಬರ್ತಿದೆ|ತುಂಬಾ ಭಯ ಆಗ್ತಿದೆ)"
]

SOLUTION_DIRECT_PATTERNS = [
    r"\b(fix (?:this|it|the)|debug|write (?:the|a) code|syntax for|how do i implement|give me the (?:code|command|steps))\b",
    r"\b(how to fix|what is the (?:error|command|syntax)|show me the code|resolve this error)\b",
    r"\b(tell me what to do|what should i run|solution for|what (?:should|can) i improve|tell me (?:what|how) (?:to|should)|tell me\s+.*\bwhat\b|how (?:can|do) i (?:improve|fix|do better))\b",
    # Telugu & Kannada direct solutions
    r"(?:కోడ్ రాయి|బగ్ ఫిక్స్ చేయి|ఎలా చేయాలో చెప్పు|సొల్యూషన్ చెప్పు|ఏం చేయాలో చెప్పు|ఎలా మెరుగుపరచాలో చెప్పు)",
    r"(?:ಕೋಡ್ ಬರೆ|ಬಗ್ ಸರಿಮಾಡು|ಹೇಗೆ ಮಾಡಬೇಕೆಂದು ಹೇಳಿ|ಪರಿಹಾರ ತಿಳಿಸಿ|ಏನು ಮಾಡಬೇಕೆಂದು ಹೇಳಿ)"
]

CONTEXT_DEPENDENT_SHORT_PHRASES = {
    "whatever": "resignation",
    "whatever, it's fine": "resignation",
    "it's fine": "resignation",
    "its fine": "resignation",
    "never mind": "withdrawal",
    "nevermind": "withdrawal",
    "forget it": "withdrawal",
    "doesn't matter": "discouragement",
    "doesnt matter": "discouragement",
    "i guess": "uncertainty",
    "sigh": "fatigue",
    "ugh": "frustration"
}


class SupportAssessmentEngine:
    """
    Advanced multi-signal support assessment engine.
    Calculates support need decoupled from emotional intensity, tracks temporal
    shifts across conversation turns, and determines Hermes activation level.
    """

    @classmethod
    def evaluate(
        cls,
        user_input: str,
        recent_history: Optional[List[Dict[str, Any]]] = None,
        previous_assessment: Optional[SupportAssessment] = None,
        active_project: Optional[str] = None
    ) -> SupportAssessment:
        text = (user_input or "").strip()
        text_lower = text.lower()
        recent_history = recent_history or []

        # 1. Evaluate context-dependent short utterances (Category D)
        is_short_phrase = len(text.split()) <= 4 and text_lower.rstrip(".!?") in CONTEXT_DEPENDENT_SHORT_PHRASES

        # 2. Extract explicit and implicit signals
        has_explicit_support = any(re.search(p, text_lower) for p in EXPLICIT_SUPPORT_PATTERNS)
        has_personal_disclosure = any(re.search(p, text_lower) for p in PERSONAL_DISCLOSURE_PATTERNS)
        has_failure_loss = any(re.search(p, text_lower) for p in FAILURE_LOSS_CONFLICT_PATTERNS)
        has_implicit_exhaustion = any(re.search(p, text_lower) for p in IMPLICIT_EXHAUSTION_PATTERNS)
        has_high_distress = any(re.search(p, text_lower) for p in DISTRESS_PATTERNS)
        has_direct_solution_request = any(re.search(p, text_lower) for p in SOLUTION_DIRECT_PATTERNS)

        # 3. Analyze recent conversation trajectory (temporal history)
        prev_distress_count = 0
        prev_negative_turns = 0
        last_turn_was_frustrated = False
        consecutive_failures = 0

        for turn in recent_history[-6:]:
            u_text = str(turn.get("user", "") if isinstance(turn, dict) else getattr(turn, "content", "")).lower()
            if any(w in u_text for w in ["error", "failing", "broken", "failed", "bug", "stuck", "frustrated", "hate", "exhausted", "tired", "sad", "bad"]):
                prev_negative_turns += 1
            if any(re.search(p, u_text) for p in FAILURE_LOSS_CONFLICT_PATTERNS + IMPLICIT_EXHAUSTION_PATTERNS + DISTRESS_PATTERNS):
                prev_distress_count += 1
            if any(w in u_text for w in ["doesn't work", "doesnt work", "still failing", "error again", "not working", "failed"]):
                consecutive_failures += 1

        if recent_history:
            last_user = str(recent_history[-1].get("user", "") if isinstance(recent_history[-1], dict) else getattr(recent_history[-1], "content", "")).lower()
            last_turn_was_frustrated = any(w in last_user for w in ["error", "broken", "failing", "stuck", "annoyed", "ugh", "failed"])

        # 4. Handle context-dependent short phrases (Category D)
        if is_short_phrase:
            if prev_negative_turns >= 2 or prev_distress_count >= 1 or consecutive_failures >= 1:
                emotion = "discouraged"
                emotion_intensity = 0.78
                support_need = 0.76
                support_type = SupportType.EMOTIONAL_SUPPORT_NEED
                solution_readiness = 0.20
                conversation_shift = "escalating_distress"
                activation_level = HermesActivationLevel.HIGH
                reason = f"Short utterance '{text}' in context of repeated prior difficulties reflects emotional resignation and withdrawal."
                return SupportAssessment(
                    emotion=emotion,
                    emotion_intensity=emotion_intensity,
                    support_need=support_need,
                    emotional_importance=0.75,
                    implicit_emotion=True,
                    primary_intent="emotional_support",
                    secondary_intent=None,
                    support_type=support_type,
                    cause="accumulated conversational friction and discouragement",
                    solution_readiness=solution_readiness,
                    conversation_shift=conversation_shift,
                    confidence=0.88,
                    support_score=round(support_need, 2),
                    activation_level=activation_level,
                    routing_reason=reason
                )
            else:
                return SupportAssessment(
                    emotion="neutral",
                    emotion_intensity=0.30,
                    support_need=0.05,
                    emotional_importance=0.10,
                    implicit_emotion=False,
                    primary_intent="casual_chat",
                    support_type=SupportType.NORMAL_CONVERSATION,
                    cause="casual banter",
                    solution_readiness=0.85,
                    conversation_shift="stable",
                    confidence=0.90,
                    support_score=0.05,
                    activation_level=HermesActivationLevel.NONE,
                    routing_reason="Casual short utterance with no prior emotional distress."
                )

        # 5. Multi-Signal Additive Scoring Computation
        support_score = 0.0
        emotion = "neutral"
        emotion_intensity = 0.30
        implicit_emotion = False
        cause = "casual conversation"
        solution_readiness = 0.80

        # Evaluate and aggregate signals
        if has_high_distress:
            emotion = "distressed"
            emotion_intensity = max(emotion_intensity, 0.90)
            support_score += 0.88
            cause = "acute emotional distress or panic"
            solution_readiness = min(solution_readiness, 0.10)

        if has_explicit_support:
            if emotion == "neutral":
                emotion = "lonely_or_seeking_comfort"
                cause = "explicit request for companionship or listening"
            emotion_intensity = max(emotion_intensity, 0.80)
            support_score += 0.75
            solution_readiness = min(solution_readiness, 0.15)

        if has_personal_disclosure:
            if emotion == "neutral":
                emotion = "vulnerable_self_doubt"
                cause = "personal vulnerability and self-doubt"
            emotion_intensity = max(emotion_intensity, 0.80)
            support_score += 0.72
            solution_readiness = min(solution_readiness, 0.25)

        if has_failure_loss:
            if emotion == "neutral":
                emotion = "discouraged_by_failure"
                cause = "disappointment following major effort or rejection"
            emotion_intensity = max(emotion_intensity, 0.80)
            support_score += 0.72
            solution_readiness = min(solution_readiness, 0.35)

        if has_implicit_exhaustion:
            if emotion == "neutral":
                emotion = "exhausted"
                cause = "burnout and cumulative emotional exhaustion"
            emotion_intensity = max(emotion_intensity, 0.78)
            support_score += 0.65
            implicit_emotion = True
            solution_readiness = min(solution_readiness, 0.20)

        if any(w in text_lower for w in ["lonely", "feeling alone", "sad", "depressed", "rough day"]):
            if emotion == "neutral":
                emotion = "sad"
                cause = "rough day or feeling isolated"
            emotion_intensity = max(emotion_intensity, 0.75)
            support_score += 0.40
            solution_readiness = min(solution_readiness, 0.30)

        if any(w in text_lower for w in ["frustrated", "annoyed", "angry", "hate this bug", "stupid code"]):
            if emotion == "neutral":
                emotion = "frustrated"
                cause = "technical friction or obstacle"
            emotion_intensity = max(emotion_intensity, 0.75)
            support_score += 0.20
            solution_readiness = max(solution_readiness, 0.85)

        if any(w in text_lower for w in ["yay", "celebrate", "it works", "finally works", "tests passed", "excited"]):
            emotion = "celebrating"
            emotion_intensity = 0.85
            support_score += 0.05
            cause = "milestone breakthrough"
            solution_readiness = 0.90

        # Factor in temporal escalation
        if prev_negative_turns >= 2:
            support_score += 0.15
        if prev_distress_count >= 1:
            support_score += 0.15
        if last_turn_was_frustrated and emotion in ["frustrated", "exhausted", "discouraged_by_failure"]:
            support_score += 0.10

        # Factor in solution readiness & intent separation
        has_practical_words = any(w in text_lower for w in ["code", "bug", "syntax", "python", "fastapi", "react", "error", "endpoint", "api", "compile", "docker", "project failing", "what should i do next"])
        is_asking_practical_next = any(w in text_lower for w in ["what should i do next", "how to move forward", "what now", "where do i start", "tell me what i should improve", "what should i improve", "how to improve", "how do i improve"])

        # Determine SupportType and Hermes Activation
        if has_high_distress:
            support_type = SupportType.HIGH_PRIORITY_DISTRESS
            primary_intent = "emotional_support"
            secondary_intent = "calming_grounding"
            activation_level = HermesActivationLevel.HIGH
            support_score = max(support_score, 0.88)
            reason = "High-priority distress signals detected; requires compassionate, careful grounding."

        elif has_direct_solution_request and not has_failure_loss and not has_personal_disclosure and not has_explicit_support:
            # "I'm frustrated with this Python error. Fix it." -> Category B
            support_type = SupportType.PRACTICAL_WITH_EMOTION
            primary_intent = "technical_problem_solving"
            secondary_intent = "frustration_acknowledgement"
            support_score = min(support_score, 0.35)
            solution_readiness = 0.95
            activation_level = HermesActivationLevel.LOW
            reason = "User is emotionally frustrated but explicitly requests direct technical solution."

        elif (has_failure_loss or has_personal_disclosure) and (is_asking_practical_next or has_practical_words or has_direct_solution_request):
            # "I failed my interview, tell me what I should improve" -> Category C
            support_type = SupportType.MIXED_SUPPORT_PRACTICAL
            primary_intent = "emotional_support"
            secondary_intent = "practical_direction"
            solution_readiness = 0.60 if (is_asking_practical_next or has_direct_solution_request) else 0.50
            support_score = max(0.65, min(0.85, support_score))
            activation_level = HermesActivationLevel.HIGH
            reason = "Mixed emotional and practical request; requires emotional acknowledgement before practical steps."

        elif has_explicit_support or support_score >= settings.HERMES_SUPPORT_HIGH_THRESHOLD or (has_failure_loss and not is_asking_practical_next and not has_direct_solution_request):
            # "I failed my interview" or "I feel lonely" -> PURE_EMOTIONAL / EMOTIONAL_SUPPORT_NEED
            support_type = SupportType.EMOTIONAL_SUPPORT_NEED
            primary_intent = "emotional_support"
            secondary_intent = None
            activation_level = HermesActivationLevel.HIGH
            support_score = max(support_score, 0.72)
            solution_readiness = min(solution_readiness, 0.20)
            reason = "User is seeking understanding, presence, or emotional validation."

        elif emotion == "celebrating":
            support_type = SupportType.EMOTIONAL_EXPRESSION
            primary_intent = "shared_celebration"
            secondary_intent = None
            activation_level = HermesActivationLevel.NONE
            support_score = 0.05
            reason = "User is celebrating a breakthrough; requires shared hype within general Saki persona."

        elif emotion in ["frustrated", "tired"] and (has_direct_solution_request or has_practical_words):
            support_type = SupportType.PRACTICAL_WITH_EMOTION
            primary_intent = "practical_inquiry"
            secondary_intent = "gentle_tone"
            support_score = min(support_score, 0.30)
            solution_readiness = 0.90
            activation_level = HermesActivationLevel.LOW
            reason = "Practical query with slight fatigue/frustration; requires crisp answer with warm tone."

        elif support_score >= settings.HERMES_SUPPORT_MODERATE_THRESHOLD:
            support_type = SupportType.EMOTIONAL_SUPPORT_NEED
            primary_intent = "emotional_support"
            secondary_intent = None
            activation_level = HermesActivationLevel.MODERATE
            reason = "Moderate emotional support need identified across conversation signals."

        elif support_score >= settings.HERMES_SUPPORT_LOW_THRESHOLD:
            support_type = SupportType.EMOTIONAL_EXPRESSION
            primary_intent = "casual_interaction"
            secondary_intent = "emotional_awareness"
            activation_level = HermesActivationLevel.LOW
            reason = "Mild emotional expression; normal model routing with empathetic tone guidance."

        else:
            support_type = SupportType.NORMAL_CONVERSATION
            primary_intent = "general_chat"
            secondary_intent = None
            activation_level = HermesActivationLevel.NONE
            reason = "Normal conversation with no meaningful emotional support requirement."

        # Cap support score to [0.0, 1.0]
        support_score = max(0.0, min(1.0, support_score))
        emotional_importance = max(support_score, emotion_intensity * 0.7)

        # Direction of shift
        conversation_shift = "stable"
        if previous_assessment:
            if support_score > previous_assessment.support_score + 0.20:
                conversation_shift = "escalating_distress"
            elif support_score < previous_assessment.support_score - 0.20:
                conversation_shift = "deescalating"
            elif support_type == SupportType.PRACTICAL_WITH_EMOTION and previous_assessment.support_type == SupportType.EMOTIONAL_SUPPORT_NEED:
                conversation_shift = "shifting_to_practical"
            elif support_type in [SupportType.EMOTIONAL_SUPPORT_NEED, SupportType.HIGH_PRIORITY_DISTRESS] and previous_assessment.support_type == SupportType.NORMAL_CONVERSATION:
                conversation_shift = "shifting_to_personal"

        return SupportAssessment(
            emotion=emotion,
            emotion_intensity=round(emotion_intensity, 2),
            support_need=round(support_score, 2),
            emotional_importance=round(emotional_importance, 2),
            implicit_emotion=implicit_emotion,
            primary_intent=primary_intent,
            secondary_intent=secondary_intent,
            support_type=support_type,
            cause=cause,
            solution_readiness=round(solution_readiness, 2),
            conversation_shift=conversation_shift,
            confidence=0.90 if not is_short_phrase else 0.85,
            support_score=round(support_score, 2),
            activation_level=activation_level,
            routing_reason=reason
        )


class TemporalEmotionTracker:
    """
    Tracks and updates emotional history across conversation sessions.
    """
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.turns: List[EmotionalTurn] = []

    def record_turn(
        self,
        user_message: str,
        assessment: SupportAssessment,
        topic: str = "general"
    ) -> EmotionalTurn:
        turn = EmotionalTurn(
            turn_index=len(self.turns) + 1,
            user_message=user_message,
            emotion=assessment.emotion,
            intensity=assessment.emotion_intensity,
            support_need=assessment.support_need,
            support_type=assessment.support_type.value,
            topic=topic,
            timestamp=time.time()
        )
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        return turn

    def get_recent_trajectory(self) -> Dict[str, Any]:
        if not self.turns:
            return {
                "trend": "stable",
                "dominant_emotion": "neutral",
                "accumulated_distress": 0.0,
                "negative_turn_count": 0
            }
        recent = self.turns[-5:]
        negative_count = sum(1 for t in recent if t.emotion in ["frustrated", "sad", "exhausted", "distressed", "vulnerable_self_doubt", "discouraged_by_failure"])
        total_support_need = sum(t.support_need for t in recent) / len(recent)

        first_need = recent[0].support_need
        last_need = recent[-1].support_need
        if last_need > first_need + 0.05 or (negative_count >= 2 and last_need >= 0.65):
            trend = "escalating"
        elif last_need < first_need - 0.05:
            trend = "deescalating"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "dominant_emotion": recent[-1].emotion,
            "accumulated_distress": round(total_support_need, 2),
            "negative_turn_count": negative_count
        }


class EmotionalSupportService:
    @staticmethod
    def assess_support_need(
        text: str,
        recent_history: Optional[List[Dict[str, Any]]] = None,
        previous_assessment: Optional[SupportAssessment] = None,
        active_project: Optional[str] = None
    ) -> SupportAssessment:
        return SupportAssessmentEngine.evaluate(
            text,
            recent_history=recent_history,
            previous_assessment=previous_assessment,
            active_project=active_project
        )


emotional_support_service = EmotionalSupportService()
