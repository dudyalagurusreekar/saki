"""
Saki Cognitive Action Engine — Capability Decision Subsystem
Determines the required action, information freshness, memory/RAG/world-access necessity,
and multi-step action plan before LLM invocation without executing external tools directly.
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# -------------------------
# ACTION TAXONOMY CONSTANTS
# -------------------------
ACTION_LOCAL_REASONING = "LOCAL_REASONING"
ACTION_MEMORY_RECALL = "MEMORY_RECALL"
ACTION_RAG_RETRIEVAL = "RAG_RETRIEVAL"
ACTION_WEB_SEARCH = "WEB_SEARCH"
ACTION_WEB_FETCH = "WEB_FETCH"
ACTION_WEB_RESEARCH = "WEB_RESEARCH"
ACTION_BROWSER_READ = "BROWSER_READ"
ACTION_BROWSER_INTERACT = "BROWSER_INTERACT"
ACTION_VISION = "VISION"
ACTION_CODING = "CODING"
ACTION_CLARIFICATION = "CLARIFICATION"
ACTION_NO_ACTION = "NO_ACTION"

ALL_ACTIONS = [
    ACTION_LOCAL_REASONING,
    ACTION_MEMORY_RECALL,
    ACTION_RAG_RETRIEVAL,
    ACTION_WEB_SEARCH,
    ACTION_WEB_FETCH,
    ACTION_WEB_RESEARCH,
    ACTION_BROWSER_READ,
    ACTION_BROWSER_INTERACT,
    ACTION_VISION,
    ACTION_CODING,
    ACTION_CLARIFICATION,
    ACTION_NO_ACTION
]

# -------------------------
# FRESHNESS REASONING CONSTANTS
# -------------------------
FRESHNESS_STABLE = "STABLE"                    # Basic math, algorithms, general knowledge
FRESHNESS_CURRENT = "CURRENT"                  # Latest software versions, CEO, recent news, pricing
FRESHNESS_LIVE = "LIVE"                        # Weather, live stock prices, active status
FRESHNESS_USER_EXPLICIT_SEARCH = "USER_EXPLICIT_SEARCH" # Explicit user trigger: "search online", "look up"
FRESHNESS_UNKNOWN = "UNKNOWN"                  # Ambiguous or uncertain freshness requirement

# Configurable confidence threshold
CONFIDENCE_THRESHOLD = 0.55


# -------------------------
# ACTION DECISION MODEL
# -------------------------
class ActionDecision(BaseModel):
    action: str = Field(default=ACTION_LOCAL_REASONING, description="Selected primary capability action")
    reason: str = Field(default="Standard local reasoning", description="Short summary justification")
    confidence: float = Field(default=0.90, description="Decision confidence 0.0 to 1.0")
    requires_memory: bool = Field(default=False)
    requires_rag: bool = Field(default=False)
    requires_world_access: bool = Field(default=False)
    requires_fresh_information: bool = Field(default=False)
    requires_user_confirmation: bool = Field(default=False)
    query_intent: str = Field(default="casual_chat")
    task_type: str = Field(default="casual_chat")
    information_need: str = Field(default="none")
    priority: str = Field(default="normal", description="low, normal, high, critical")
    fallback_action: str = Field(default=ACTION_LOCAL_REASONING)
    freshness_requirement: str = Field(default=FRESHNESS_STABLE)
    context_requirements: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    planned_actions: List[str] = Field(default_factory=lambda: [ACTION_LOCAL_REASONING])
    decision_status: str = Field(default="SUCCESS", description="SUCCESS, FALLBACK, DEGRADED")


# -------------------------
# INTENT PATTERNS
# -------------------------
EXPLICIT_SEARCH_PATTERNS = [
    r"\b(search online|look up|check online|find online|google|browse for|search the web|do a search|search for)\b",
    r"\b(latest|current|today's|news about|recent updates on|what is the price of|weather in|who is the current)\b"
]

EXPLICIT_URL_PATTERNS = [
    r"https?://[^\s]+",
    r"\b(read this url|read this page|extract webpage|summarize page|fetch link)\b"
]

DEEP_RESEARCH_PATTERNS = [
    r"\b(compare|multi-source|deep research|comprehensive study|in-depth comparison|thorough analysis of multiple)\b"
]

BROWSER_INTERACT_PATTERNS = [
    r"\b(click on|form submit|navigate to|open site and|log in to|fill form)\b"
]

BROWSER_READ_PATTERNS = [
    r"\b(inspect dom|read website|view web page|open this site|browser view)\b"
]

MEMORY_PATTERNS = [
    r"\b(do you remember|what did i say|my preferences|what is my name|who am i|our last chat|remind me|my project|did i choose|my decision|what laptop did i|what are my goals)\b"
]


RAG_PATTERNS = [
    r"\b(uploaded pdf|my document|in my file|project report|uploaded file|document says|file content)\b"
]

CODING_PATTERNS = [
    r"```[a-zA-Z]*",
    r"\b(write a function|implement|fix this bug|traceback|syntaxerror|fastapi|react|python script|java program|sql query|code snippet|debug this)\b"
]

VISION_KEYWORDS = [
    "screenshot", "this image", "in this picture", "this diagram", "read text from photo", "visual layout", "what is in this photo"
]


# -------------------------
# HYBRID ACTION DECISION ENGINE
# -------------------------
def classify_freshness(query: str) -> str:
    """Classifies the information freshness requirement of a user query."""
    q_lower = query.lower()
    
    if any(re.search(p, q_lower) for p in EXPLICIT_SEARCH_PATTERNS[:1]):
        return FRESHNESS_USER_EXPLICIT_SEARCH
        
    if any(w in q_lower for w in ["weather", "live price", "stock price", "active status", "current rate", "live score"]):
        return FRESHNESS_LIVE

    if any(w in q_lower for w in ["latest", "current", "2026", "news", "recent", "today", "update", "newest", "who is current"]):
        return FRESHNESS_CURRENT

    if any(w in q_lower for w in ["what is", "how to", "definition", "algorithm", "formula", "explain", "history of", "math"]):
        return FRESHNESS_STABLE

    return FRESHNESS_UNKNOWN


def decide_action(
    query: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    memory_data: Optional[Dict[str, Any]] = None,
    task_type: Optional[str] = None,
    is_coding: bool = False,
    has_image: bool = False
) -> ActionDecision:
    """
    Executes local hybrid action decision pipeline without making external network tool calls.
    """
    try:
        q_text = (query or "").strip()
        q_lower = q_text.lower()
        attachments = attachments or []
        
        # 1. Vision Check
        has_image_attachment = has_image or any(
            att.get("type") in ["image", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"] 
            or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            for att in attachments
        )
        if has_image_attachment or any(kw in q_lower for kw in VISION_KEYWORDS):
            return ActionDecision(
                action=ACTION_VISION,
                reason="Input contains an image or explicit visual inspection request.",
                confidence=0.98,
                requires_world_access=False,
                requires_fresh_information=False,
                query_intent="vision_inspection",
                task_type="vision_analysis",
                information_need="visual_content",
                priority="normal",
                freshness_requirement=FRESHNESS_STABLE,
                planned_actions=[ACTION_VISION, ACTION_LOCAL_REASONING]
            )

        # 2. Browser Interact Check
        if any(re.search(p, q_lower) for p in BROWSER_INTERACT_PATTERNS):
            return ActionDecision(
                action=ACTION_BROWSER_INTERACT,
                reason="User requested interactive browser action or form navigation.",
                confidence=0.92,
                requires_world_access=True,
                requires_fresh_information=True,
                requires_user_confirmation=True,
                query_intent="browser_interaction",
                task_type="browser_action",
                information_need="web_page_interaction",
                priority="high",
                freshness_requirement=FRESHNESS_LIVE,
                planned_actions=[ACTION_BROWSER_INTERACT]
            )

        # 3. Browser Read Check
        if any(re.search(p, q_lower) for p in BROWSER_READ_PATTERNS):
            return ActionDecision(
                action=ACTION_BROWSER_READ,
                reason="User requested browser DOM inspection or website page reading.",
                confidence=0.90,
                requires_world_access=True,
                requires_fresh_information=True,
                query_intent="web_page_read",
                task_type="browser_read",
                information_need="web_dom_content",
                priority="normal",
                freshness_requirement=FRESHNESS_CURRENT,
                planned_actions=[ACTION_BROWSER_READ, ACTION_LOCAL_REASONING]
            )

        # 4. Explicit Web Fetch (URL) Check
        if any(re.search(p, q_lower) for p in EXPLICIT_URL_PATTERNS):
            return ActionDecision(
                action=ACTION_WEB_FETCH,
                reason="User provided a URL or requested reading a specific webpage.",
                confidence=0.96,
                requires_world_access=True,
                requires_fresh_information=True,
                query_intent="web_fetch",
                task_type="web_fetch",
                information_need="url_content",
                priority="normal",
                freshness_requirement=FRESHNESS_CURRENT,
                planned_actions=[ACTION_WEB_FETCH, ACTION_LOCAL_REASONING]
            )

        # 5. Deep Web Research Check (Multi-source comparison)
        if any(re.search(p, q_lower) for p in DEEP_RESEARCH_PATTERNS) and any(w in q_lower for w in ["latest", "current", "compare", "models", "options", "sources"]):
            return ActionDecision(
                action=ACTION_WEB_RESEARCH,
                reason="User requested multi-source synthesis or comprehensive research.",
                confidence=0.92,
                requires_world_access=True,
                requires_fresh_information=True,
                query_intent="deep_research",
                task_type="web_research",
                information_need="multi_source_synthesis",
                priority="normal",
                freshness_requirement=FRESHNESS_CURRENT,
                planned_actions=[ACTION_MEMORY_RECALL, ACTION_WEB_RESEARCH, ACTION_LOCAL_REASONING]
            )

        # 6. Explicit / Time-Sensitive Web Search Check
        freshness = classify_freshness(q_text)
        is_explicit_search = freshness in [FRESHNESS_USER_EXPLICIT_SEARCH, FRESHNESS_CURRENT, FRESHNESS_LIVE] or any(re.search(p, q_lower) for p in EXPLICIT_SEARCH_PATTERNS)
        
        if is_explicit_search:
            return ActionDecision(
                action=ACTION_WEB_SEARCH,
                reason="Request requires fresh, current, or time-sensitive public information.",
                confidence=0.95,
                requires_world_access=True,
                requires_fresh_information=True,
                query_intent="current_information",
                task_type="information_request",
                information_need="latest_public_data",
                priority="normal",
                freshness_requirement=freshness,
                planned_actions=[ACTION_WEB_SEARCH, ACTION_LOCAL_REASONING]
            )

        # 7. Personal Memory Recall Check
        has_memory_pattern = any(re.search(p, q_lower) for p in MEMORY_PATTERNS)
        if has_memory_pattern:
            return ActionDecision(
                action=ACTION_MEMORY_RECALL,
                reason="User asked a question about personal identity, preferences, or past conversation.",
                confidence=0.95,
                requires_memory=True,
                requires_world_access=False,
                requires_fresh_information=False,
                query_intent="personal_memory",
                task_type="memory_recall",
                information_need="user_durable_memory",
                priority="normal",
                freshness_requirement=FRESHNESS_STABLE,
                planned_actions=[ACTION_MEMORY_RECALL, ACTION_LOCAL_REASONING]
            )

        # 8. RAG / Local Document Check
        if any(re.search(p, q_lower) for p in RAG_PATTERNS) or any(att.get("type") in ["document", ".pdf", ".docx", ".txt"] for att in attachments):
            return ActionDecision(
                action=ACTION_RAG_RETRIEVAL,
                reason="User referenced an uploaded document or project knowledge file.",
                confidence=0.94,
                requires_rag=True,
                requires_world_access=False,
                requires_fresh_information=False,
                query_intent="document_query",
                task_type="rag_retrieval",
                information_need="document_knowledge",
                priority="normal",
                freshness_requirement=FRESHNESS_STABLE,
                planned_actions=[ACTION_RAG_RETRIEVAL, ACTION_LOCAL_REASONING]
            )

        # 9. Coding / Programming Check
        if is_coding or any(re.search(p, q_lower) for p in CODING_PATTERNS):
            return ActionDecision(
                action=ACTION_CODING,
                reason="Request involves code implementation, syntax analysis, or debugging.",
                confidence=0.96,
                requires_world_access=False,
                requires_fresh_information=False,
                query_intent="code_assistance",
                task_type="coding_task",
                information_need="code_implementation",
                priority="normal",
                freshness_requirement=FRESHNESS_STABLE,
                planned_actions=[ACTION_CODING, ACTION_LOCAL_REASONING]
            )

        # 10. Ambiguous / Low Confidence Check
        if len(q_text) < 4 and q_lower not in ["hi", "hey", "hello", "yes", "no"]:
            return ActionDecision(
                action=ACTION_CLARIFICATION,
                reason="Query is ambiguous or too short to determine clear capability action.",
                confidence=0.45,
                requires_world_access=False,
                requires_fresh_information=False,
                query_intent="ambiguous",
                task_type="clarification",
                information_need="clarification",
                priority="normal",
                fallback_action=ACTION_LOCAL_REASONING,
                freshness_requirement=FRESHNESS_STABLE,
                planned_actions=[ACTION_CLARIFICATION]
            )

        # 11. Unknown + Stable vs Unknown + Current Matrix
        if freshness == FRESHNESS_UNKNOWN and any(w in q_lower for w in ["who", "what", "where", "when"]):
            # Stable unknown -> Local Reasoning
            return ActionDecision(
                action=ACTION_LOCAL_REASONING,
                reason="Question involves general knowledge that can be answered from local model weights.",
                confidence=0.85,
                requires_world_access=False,
                requires_fresh_information=False,
                query_intent="casual_chat",
                task_type="general_reasoning",
                information_need="general_knowledge",
                priority="normal",
                freshness_requirement=FRESHNESS_STABLE,
                planned_actions=[ACTION_LOCAL_REASONING]
            )

        # Default: Local Reasoning
        return ActionDecision(
            action=ACTION_LOCAL_REASONING,
            reason="Standard conversational query processed via local intelligence.",
            confidence=0.90,
            requires_world_access=False,
            requires_fresh_information=False,
            query_intent="casual_chat",
            task_type="casual_chat",
            information_need="none",
            priority="normal",
            freshness_requirement=FRESHNESS_STABLE,
            planned_actions=[ACTION_LOCAL_REASONING]
        )

    except Exception as e:
        # Fallback safety net — never crash the system
        return ActionDecision(
            action=ACTION_LOCAL_REASONING,
            reason=f"Action engine error fallback: {str(e)}",
            confidence=0.50,
            requires_world_access=False,
            requires_fresh_information=False,
            fallback_action=ACTION_LOCAL_REASONING,
            decision_status="FALLBACK"
        )
