import re
import json
from typing import Dict, Any, List, Tuple, Optional
from brain.schemas import IntentResult
from backend.services.ai_service import call_model

# Taxonomy of all 15 intents
INTENTS = [
    "Coding", "Debugging", "Research", "Memory", "Project",
    "Learning", "Planning", "Current Events", "News", "Math",
    "Casual Chat", "Writing", "Translation", "Vision", "Image Generation"
]

# Rule-based keyword matching profiles
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "Coding": [
        "code", "program", "function", "class", "script", "syntax", "compile", "develop",
        "implementation", "write a", "how to implement", "create a function"
    ],
    "Debugging": [
        "error", "bug", "exception", "traceback", "fails", "failing", "crash", "wrong output",
        "doesn't work", "issue", "troubleshoot", "why is this", "broken", "fix this"
    ],
    "Research": [
        "research", "paper", "scientific", "study", "analysis", "compare", "literature",
        "investigate", "explain how", "background of", "difference between"
    ],
    "Memory": [
        "remember", "forget", "recall", "past conversation", "what did I say", "remind me",
        "conversation history", "our last chat", "durable memory"
    ],
    "Project": [
        "repository", "workspace", "folder structure", "project docs", "readme", "files in my",
        "active directory", "project files", "saki config", "build system"
    ],
    "Learning": [
        "teach me", "learn", "how does", "tutorial", "explain to a beginner", "concept of",
        "what is the meaning", "study guide"
    ],
    "Planning": [
        "plan", "roadmap", "steps to", "schedule", "tasks", "todo", "milestones", "workflow",
        "how should I organize", "strategy"
    ],
    "Current Events": [
        "current events", "latest news", "happening now", "today's events", "what is happening",
        "recent developments"
    ],
    "News": [
        "news", "headline", "newspaper", "current affairs", "world news", "latest updates"
    ],
    "Math": [
        "math", "calculate", "solve", "equation", "formula", "addition", "subtraction",
        "multiplication", "division", "integral", "derivative", "sum of", "algebra", "geometry"
    ],
    "Casual Chat": [
        "hi", "hello", "hey", "how are you", "what's up", "good morning", "good night",
        "nice to meet you", "thank you", "thanks", "joke", "funny"
    ],
    "Writing": [
        "write an essay", "draft a email", "compose", "paraphrase", "summarize text",
        "rewrite", "grammar check", "article", "letter", "resume"
    ],
    "Translation": [
        "translate", "in Spanish", "in French", "in Telugu", "in Hindi", "how do you say",
        "meaning of word in", "foreign language"
    ],
    "Vision": [
        "image description", "what is in this picture", "analyze this image", "ocr",
        "read text from photo", "visual analysis"
    ],
    "Image Generation": [
        "generate image", "create a picture", "draw a", "generate a photo", "dall-e",
        "midjourney", "stable diffusion", "render a scene"
    ]
}

def rule_based_classify(text: str) -> Tuple[Optional[str], float]:
    """Perform rule-based intent classification by counting keyword hits."""
    text_lower = text.lower()
    scores = {intent: 0 for intent in INTENTS}
    
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            # Look for word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(kw)}\b'
            matches = len(re.findall(pattern, text_lower))
            scores[intent] += matches * 1.5
            
            # Simple substring match fallback for compound words
            if kw in text_lower and matches == 0:
                scores[intent] += 0.5
                
    # Find the top intent and score
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_intent, top_score = sorted_scores[0]
    
    if top_score > 2.0:
        # Normalize confidence score
        confidence = min(0.95, 0.5 + (top_score / 10.0))
        return top_intent, confidence
        
    return None, 0.0

def llm_classify(text: str) -> Tuple[str, float]:
    """Query the local Ollama LLM to classify intent."""
    prompt = f"""
Classify the following user query into exactly one of these 15 intents:
{", ".join(INTENTS)}

Respond ONLY with a JSON object in this format:
{{
  "intent": "Selected Intent",
  "confidence": 0.95
}}

User query: "{text}"
"""
    try:
        response = call_model(prompt)
        # Try to parse JSON from response
        # Find JSON boundaries
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            intent = data.get("intent", "").strip()
            confidence = float(data.get("confidence", 0.8))
            
            # Clean matching of intent names (case-insensitive search)
            for standard_intent in INTENTS:
                if standard_intent.lower() == intent.lower():
                    return standard_intent, min(1.0, max(0.0, confidence))
    except Exception:
        pass
        
    return "Casual Chat", 0.5

def classify_intent(text: str, skip_llm: bool = False) -> IntentResult:
    """
    Classifies the user query's intent.
    Uses fast rule-based classifier first, falling back to LLM or keyword ranking.
    """
    if not text or not text.strip():
        return IntentResult(intent="Casual Chat", confidence=1.0)
        
    # 1. Rule-based check
    intent, confidence = rule_based_classify(text)
    if intent and confidence >= 0.8:
        return IntentResult(intent=intent, confidence=confidence)
        
    # 2. LLM classification fallback
    if not skip_llm:
        intent, confidence = llm_classify(text)
        return IntentResult(intent=intent, confidence=confidence)
        
    # 3. Simple keyword fallback (if LLM skipped/failed)
    # Re-evaluate with lower confidence threshold
    text_lower = text.lower()
    scores = {i: 0 for i in INTENTS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[intent] += 1
                
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_intent, top_score = sorted_scores[0]
    
    if top_score > 0:
        return IntentResult(intent=top_intent, confidence=0.6)
        
    return IntentResult(intent="Casual Chat", confidence=0.4)
