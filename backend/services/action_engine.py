"""
Saki Cognitive Action Engine — Capability Decision Subsystem
Determines the required action, information freshness, memory/RAG/world-access necessity,
and multi-step action plan before LLM invocation without executing external tools directly.
Sprint 1: Unified date-aware (2026), local entity, and recommendation classification.
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


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
FRESHNESS_CURRENT = "CURRENT"                  # Latest software versions, CEO, recent news, 2026 data
FRESHNESS_CURRENT_EXTERNAL_FACT = "CURRENT_EXTERNAL_FACT"  # Current version/release queries requiring real external evidence
FRESHNESS_LIVE = "LIVE"                        # Weather, live stock prices, active status
FRESHNESS_USER_EXPLICIT_SEARCH = "USER_EXPLICIT_SEARCH" # Explicit user trigger: "search online", "look up"
FRESHNESS_UNKNOWN = "UNKNOWN"                  # Ambiguous or uncertain freshness requirement

from datetime import datetime

def get_runtime_datetime() -> datetime:
    return datetime.now()

def get_runtime_year() -> int:
    return datetime.now().year

def get_runtime_month() -> str:
    return datetime.now().strftime("%B")

def get_runtime_date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

# Reference Date Anchor (dynamic)
SYSTEM_CURRENT_YEAR = get_runtime_year()
SYSTEM_CURRENT_MONTH = get_runtime_month()

# Configurable confidence threshold
CONFIDENCE_THRESHOLD = 0.55


# -------------------------
# QUERY UNDERSTANDING MODEL
# -------------------------
class QueryUnderstanding(BaseModel):
    original_query: str = Field(default="")
    normalized_query: str = Field(default="")
    primary_entity: Optional[str] = Field(default=None)
    entity_type: Optional[str] = Field(default=None, description="location, software, concept, media, hardware, general, ambiguous")
    location: Optional[str] = Field(default=None)
    topic: Optional[str] = Field(default=None, description="food, tourism, weather, history, software_version, software_framework, movies, news, casual, concept")
    intent: Optional[str] = Field(default=None, description="recommendation, factual_lookup, explanation, live_update, version_query, casual_chat")
    temporal_requirement: str = Field(default=FRESHNESS_STABLE)
    recommendation_requirement: bool = Field(default=False)
    required_information: Optional[str] = Field(default=None)
    is_ambiguous: bool = Field(default=False)
    search_query_optimized: Optional[str] = Field(default=None)


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
    temporal_requirement: str = Field(default=FRESHNESS_STABLE, description="Explicit temporal freshness requirement (STABLE, CURRENT, LIVE, USER_EXPLICIT_SEARCH)")
    query_understanding: Optional[QueryUnderstanding] = Field(default=None, description="Structured semantic query representation")
    context_requirements: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    planned_actions: List[str] = Field(default_factory=lambda: [ACTION_LOCAL_REASONING])
    decision_status: str = Field(default="SUCCESS", description="SUCCESS, FALLBACK, DEGRADED")

    @model_validator(mode="after")
    def sync_temporal_fields(self):
        if self.freshness_requirement and self.temporal_requirement == FRESHNESS_STABLE:
            self.temporal_requirement = self.freshness_requirement
        return self


# -------------------------
# INTENT PATTERNS
# -------------------------
EXPLICIT_SEARCH_PATTERNS = [
    r"\b(search online|look up|check online|find online|google|browse for|search the web|do a search|search for)\b",
    r"\b(latest|current|today's|news about|recent updates on|what is the price of|weather in|who is the current)\b",
    r"\b(right now|happening in.*now|happening in.*right now|what is happening in.*today)\b"
]

TEMPORAL_FRESHNESS_PATTERNS = [
    r"\b(2026|2027|this year|this month|this week|today|now|right now|latest|current|currently|recently|recent|upcoming|newest)\b",
    r"\b(good movies in 2026|best movies in 2026|movies.*2026|releases in 2026|developments in.*2026|movies in 2027|releases in 2027)\b",
    r"\b(what happened in.*today|what is new in|latest release|latest version|current version|current ceo|current president|current prime minister)\b"
]

LOCAL_AND_REGIONAL_PATTERNS = [
    # Food and culinary recommendations
    r"\b(special food|famous food|local food|best food|special dish|famous dishes|restaurants|where to eat|street food)\b",
    # Places to visit, travel, and attractions
    r"\b(places to visit|special places|best places|tourist places|sightseeing|attractions|things to do|what should i visit|visit this weekend)\b",
    # Monuments, heritage, and obscure entities
    r"\b(temple|mandir|kovil|gudi|monument|fort|kambadur|lepakshi|malleswara|mallikarjuna|cave|waterfall|dam|ghat|peetham|mutt|kshetram)\b",
    r"\b(village|taluk|mandal|district|panchayat|heritage site|ancient site|archaeological site|obscure local)\b",
    r"\b(local festival|district administration|heritage monument|chalukyan|vijayanagara|chola|pallava|hoysala)\b",
    # Exploratory highlights
    r"\b(what is special in|what is special about|tell me about.*in|help me to know what special)\b"
]

LOCATION_NAME_PATTERNS = [
    r"\b(vijayawada|andhra|andhra pradesh|anantapur|tadipatri|kambadur|lepakshi|tirupati|guntur|visakhapatnam|hyderabad|bengaluru|bangalore|chennai|delhi|mumbai|kolkata|india)\b"
]

RECOMMENDATION_PATTERNS = [
    r"\b(good movies|best movies|recommend movies|top movies|movie recommendations)\b",
    r"\b(best places to visit|what to visit this weekend|weekend trip|recommend places)\b",
    r"\b(best restaurants|good restaurants|top places to eat)\b"
]

PERSONAL_STATEMENT_PATTERNS = [
    r"\b(i am currently working on|i am working on|i'm working on|my project is|my favorite|i prefer|i like to use|we decided to|we decided that)\b",
    r"\b(do you remember|what did i say|what is my name|who am i|our last chat|remind me|what project am i|what was my)\b"
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
    r"\b(do you remember|what did i say|my preferences|what is my name|who am i|our last chat|remind me|my project|did i choose|my decision|what laptop did i|what are my goals|what project am i|what were we working on|what did we decide)\b"
]

RAG_PATTERNS = [
    r"\b(uploaded pdf|my document|in my file|project report|uploaded file|document says|file content)\b"
]

CODING_PATTERNS = [
    r"```[a-zA-Z]*",
    r"\b(write a function|implement|fix this bug|traceback|syntaxerror|nameerror|typeerror|fastapi|react|python script|java program|sql query|code snippet|debug this|def add\(|reverse a string)\b"
]

STATIC_KNOWLEDGE_PATTERNS = [
    r"^(what is|what are|explain|describe|definition of|how does|why does|difference between|who invented)\s+[a-z0-9\s]+$"
]

# -------------------------
# CURRENT EXTERNAL FACT PATTERNS
# Queries that REQUIRE real external evidence — model pretrained knowledge is NOT sufficient
# -------------------------
CURRENT_EXTERNAL_FACT_PATTERNS = [
    r"\b(current|latest|newest|recent)\s+(version|release|update)\b",
    r"\b(latest|current|newest)\s+(python|fastapi|node\.?js|nodejs|ollama|react|docker|pytorch|pydantic|next\.?js|nextjs|postgresql|postgres|java|go|rust|ruby|php|swift|kotlin|typescript|npm|pip|cargo|gradle|maven)\b",
    r"\b(python|fastapi|node\.?js|nodejs|ollama|react|docker|pytorch|pydantic|next\.?js|nextjs|postgresql|java|go|rust|ruby|php|swift|kotlin|typescript)\s+(latest|current|newest)\s*(version|release)?\b",
    r"\b(latest|current|newest)\s+release\b",
    r"\b(what|which)\s+(?:is\s+)?(?:the\s+)?(?:current|latest|newest)\s+(?:stable\s+)?version\b",
    r"\bcurrent\s+(?:stable\s+)?version\s+(?:of|for|in)\b",
    r"\bversion\s+(?:of\s+)?(?:python|fastapi|node|ollama|react|docker)\s+(?:is\s+)?(?:out|available|released)\b",
]

CURRENT_TIME_PATTERNS = [
    r"\b(what\s+time|current\s+time|exact\s+time|time\s+(?:is\s+it|right\s+now))\b",
    r"\b(what\s+(?:is\s+)?(?:today'?s?\s+)?date|today'?s?\s+date|current\s+date|exact\s+date)\b",
    r"\b(what\s+day\s+is\s+(?:it|today))\b",
]


def is_current_external_fact_query(query: str) -> bool:
    """Detects if query requires current external evidence (e.g. software versions, releases).
    These MUST NOT be answered from stale model knowledge."""
    q_lower = query.lower().strip()
    return any(re.search(p, q_lower) for p in CURRENT_EXTERNAL_FACT_PATTERNS)


def is_current_time_query(query: str) -> bool:
    """Detects if query is asking for current time/date (answerable from runtime clock)."""
    q_lower = query.lower().strip()
    return any(re.search(p, q_lower) for p in CURRENT_TIME_PATTERNS)


VISION_KEYWORDS = [
    "screenshot", "this image", "in this picture", "this diagram", "read text from photo", "visual layout", "what is in this photo"
]


# -------------------------
# HYBRID ACTION DECISION ENGINE
# -------------------------
def is_personal_memory_statement(query: str) -> bool:
    """Detects if query is a personal statement, user declaration, or memory query."""
    q_lower = query.lower().strip()
    return any(re.search(p, q_lower) for p in PERSONAL_STATEMENT_PATTERNS)


def is_local_or_recommendation_query(query: str) -> bool:
    """
    Detects if query is about local food, places to visit, regional heritage,
    travel recommendations, or current-year recommendations.
    """
    q_lower = query.lower().strip()
    
    # 1. Personal statements never qualify as local web queries
    if is_personal_memory_statement(query):
        return False

    # 2. Local info + Location match
    has_local_topic = any(re.search(p, q_lower) for p in LOCAL_AND_REGIONAL_PATTERNS)
    has_location = any(re.search(p, q_lower) for p in LOCATION_NAME_PATTERNS)
    if has_local_topic and (has_location or any(w in q_lower for w in ["near me", "this weekend", "local", "obscure", "heritage", "special"])):
        return True

    # 3. Recommendations with temporal or local scope (e.g., "good movies in 2026")
    has_rec = any(re.search(p, q_lower) for p in RECOMMENDATION_PATTERNS)
    has_time_or_loc = any(re.search(p, q_lower) for p in TEMPORAL_FRESHNESS_PATTERNS + LOCATION_NAME_PATTERNS)
    if has_rec and (has_time_or_loc or "2026" in q_lower or "this weekend" in q_lower or "today" in q_lower):
        return True

    # 4. Obscure / local entity inquiries
    if any(re.search(p, q_lower) for p in [
        r"\b(temple|monument|fort|kambadur|lepakshi|cave|heritage site)\b",
        r"\b(tell me about.*temple|who built.*fort|what is special about.*temple|obscure.*place)\b"
    ]):
        return True

    return False


def classify_freshness(query: str, runtime_year: Optional[int] = None) -> str:
    """
    Classifies the information freshness requirement of a user query.
    Dynamically anchored to runtime year (e.g. 2026).
    """
    if runtime_year is None:
        runtime_year = get_runtime_year()

    q_lower = query.lower().strip()

    # Guard: Personal memory statements are stable internal facts
    if is_personal_memory_statement(query):
        return FRESHNESS_STABLE

    # CURRENT_EXTERNAL_FACT: version/release queries that MUST have real external evidence
    # This check MUST come before generic CURRENT to ensure distinct classification
    if is_current_external_fact_query(query):
        return FRESHNESS_CURRENT_EXTERNAL_FACT

    # Explicit user search commands
    if any(re.search(p, q_lower) for p in EXPLICIT_SEARCH_PATTERNS[:1]):
        return FRESHNESS_USER_EXPLICIT_SEARCH

    # Live sensor/price metrics
    if any(w in q_lower for w in ["weather", "live price", "stock price", "active status", "current rate", "live score", "traffic"]):
        return FRESHNESS_LIVE

    # Dynamic year detection
    years_in_query = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", q_lower)]
    has_temporal_keywords = any(k in q_lower for k in ["latest", "current", "upcoming", "now", "today", "recent", "this year", "this month", "newest"])

    if years_in_query:
        # All years are strictly past years and no current/live intent
        if all(y < runtime_year for y in years_in_query) and not has_temporal_keywords:
            return FRESHNESS_STABLE
        # Contains current year or future year
        if any(y >= runtime_year for y in years_in_query):
            return FRESHNESS_CURRENT

    # Current / temporal freshness expressions
    if any(re.search(p, q_lower) for p in TEMPORAL_FRESHNESS_PATTERNS):
        return FRESHNESS_CURRENT

    # Local / location-specific information / recommendations
    if is_local_or_recommendation_query(query):
        return FRESHNESS_CURRENT

    # Static general knowledge
    if any(re.search(p, q_lower) for p in STATIC_KNOWLEDGE_PATTERNS) and not any(k in q_lower for k in ["latest", "current", "news", "today", "now", "version"]):
        return FRESHNESS_STABLE

    if any(w in q_lower for w in ["what is", "how to", "definition", "algorithm", "formula", "explain", "history of", "math"]):
        if not any(k in q_lower for k in ["latest", "current", "news", "today", "now", "version"]):
            return FRESHNESS_STABLE

    return FRESHNESS_UNKNOWN


# -------------------------
# KNOWN ENTITY REGISTRIES FOR QUERY UNDERSTANDING
# -------------------------
KNOWN_LOCATIONS = {
    "vijayawada": "Vijayawada",
    "hyderabad": "Hyderabad",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "chennai": "Chennai",
    "delhi": "Delhi",
    "mumbai": "Mumbai",
    "kolkata": "Kolkata",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "tirupati": "Tirupati",
    "guntur": "Guntur",
    "anantapur": "Anantapur",
    "tadipatri": "Tadipatri",
    "kambadur": "Kambadur",
    "lepakshi": "Lepakshi",
    "andhra pradesh": "Andhra Pradesh",
    "andhra": "Andhra Pradesh",
    "telangana": "Telangana",
    "karnataka": "Karnataka",
    "india": "India"
}

KNOWN_TECH_ENTITIES = {
    "fastapi": "FastAPI",
    "python": "Python",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "ollama": "Ollama",
    "react": "React",
    "pytorch": "PyTorch",
    "docker": "Docker",
    "pydantic": "Pydantic",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "nvidia gpu": "NVIDIA GPU",
    "nvidia": "NVIDIA"
}

AMBIGUOUS_ENTITIES = {
    "saki": "Saki",
    "gemini": "Gemini",
    "apple": "Apple"
}


def parse_query_understanding(query: str) -> QueryUnderstanding:
    """
    Parses structured QueryUnderstanding representation:
    - Primary entity & entity type
    - Location vs Topic separation
    - User intent & required information
    - Temporal & recommendation requirements
    - Search query optimization
    """
    q_clean = (query or "").strip()
    q_lower = q_clean.lower()
    
    qu = QueryUnderstanding(
        original_query=q_clean,
        normalized_query=re.sub(r"[^\w\s\.\-]", " ", q_lower).strip()
    )
    
    # 1. Location & Entity Detection
    # Separate specific localities from broad states/regions
    broad_regions = {"andhra pradesh", "andhra", "telangana", "karnataka", "india"}
    specific_locs = {k: v for k, v in KNOWN_LOCATIONS.items() if k not in broad_regions}
    broad_locs = {k: v for k, v in KNOWN_LOCATIONS.items() if k in broad_regions}

    found_loc = None
    # Check specific localities first
    for loc_key, loc_val in sorted(specific_locs.items(), key=lambda x: -len(x[0])):
        if re.search(r"\b" + re.escape(loc_key) + r"\b", q_lower):
            found_loc = loc_val
            break

    # If no specific locality, check broad regions
    if not found_loc:
        for loc_key, loc_val in sorted(broad_locs.items(), key=lambda x: -len(x[0])):
            if re.search(r"\b" + re.escape(loc_key) + r"\b", q_lower):
                found_loc = loc_val
                break

    if found_loc:
        qu.location = found_loc
        qu.primary_entity = found_loc
        qu.entity_type = "location"

    # Specific Landmark / Temple / Monument Entity Extraction
    landmark_match = re.search(r"\b([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)\s+(temple|mandir|fort|barrage|caves?|dam|falls|museum|palace)\b", q_clean, re.IGNORECASE)
    if landmark_match:
        qu.primary_entity = landmark_match.group(0).strip()
        qu.entity_type = "landmark"

    # Specific Named Entity extraction (e.g. "city FooBarBaz", "town FooBar")
    named_match = re.search(r"\b(?:city|town|village|place)\s+([A-Za-z0-9_]+)\b", q_clean, re.IGNORECASE)
    if named_match:
        qu.primary_entity = named_match.group(1).strip()
        qu.location = named_match.group(1).strip()
        qu.entity_type = "location"

    # 2. Software / Tech Entity Detection
    found_tech = None
    for tech_key, tech_val in sorted(KNOWN_TECH_ENTITIES.items(), key=lambda x: -len(x[0])):
        if re.search(r"\b" + re.escape(tech_key) + r"\b", q_lower):
            found_tech = tech_val
            break
            
    if found_tech:
        qu.primary_entity = found_tech
        qu.entity_type = "hardware" if "nvidia" in found_tech.lower() else "software"

    # 3. Media Entity Detection
    if any(m in q_lower for m in ["movie", "movies", "film", "films"]):
        if not qu.primary_entity:
            qu.primary_entity = "movies"
            qu.entity_type = "media"

    # 4. Ambiguous Entities Check (Part 9)
    for amb_key, amb_val in AMBIGUOUS_ENTITIES.items():
        if re.search(r"\b" + re.escape(amb_key) + r"\b", q_lower):
            words = q_lower.split()
            if len(words) <= 4 and not any(w in q_lower for w in ["ai", "assistant", "api", "framework", "fruit", "phone", "model", "llm"]):
                qu.primary_entity = amb_val
                qu.entity_type = "ambiguous"
                qu.is_ambiguous = True

    # 5. Topic & Intent Classification
    freshness = classify_freshness(q_clean)
    qu.temporal_requirement = freshness

    # Food
    if any(re.search(p, q_lower) for p in [r"\b(food|special food|famous food|dishes|dish|restaurants|street food|cuisine|sweets|eat)\b"]):
        qu.topic = "food"
        qu.intent = "recommendation"
        qu.recommendation_requirement = True
        qu.required_information = "local culinary specialties, notable traditional dishes, and food recommendations"
        if qu.location:
            qu.search_query_optimized = f"special food traditional dishes {qu.location}"

    # Tourism / Places to visit
    elif any(re.search(p, q_lower) for p in [r"\b(places to visit|tourist places|sightseeing|attractions|things to do|what to visit|visit this weekend)\b"]):
        qu.topic = "tourism"
        qu.intent = "recommendation"
        qu.recommendation_requirement = True
        qu.required_information = "notable places to visit, landmarks, and tourist attractions"
        if qu.location:
            qu.search_query_optimized = f"best places to visit tourist attractions {qu.location}"

    # Weather
    elif any(re.search(p, q_lower) for p in [r"\b(weather|temperature|forecast|climate|rain|live weather)\b"]):
        qu.topic = "weather"
        qu.intent = "live_update"
        qu.required_information = "current temperature, weather conditions, and forecast"
        if qu.location:
            qu.search_query_optimized = f"current weather live forecast {qu.location}"

    # History
    elif any(re.search(p, q_lower) for p in [r"\b(history|history of|ancient|origins|heritage|who built|architecture|ruling dynasty)\b"]):
        qu.topic = "history"
        qu.intent = "factual_lookup"
        qu.required_information = "historical background, origins, and cultural heritage"
        if qu.location:
            qu.search_query_optimized = f"history historical heritage {qu.location}"

    # Software Version
    elif any(re.search(p, q_lower) for p in [r"\b(latest version|current version|new release|release notes|version|latest release|newest version)\b"]):
        qu.topic = "software_version"
        qu.intent = "version_query"
        qu.required_information = "current official software version number and release details"
        if qu.primary_entity:
            qu.search_query_optimized = f"latest {qu.primary_entity} version official release"

    # General Software Framework Explanation
    elif qu.entity_type == "software" and any(re.search(p, q_lower) for p in [r"^(what is|explain|describe|definition of|how does)\b"]):
        qu.topic = "software_framework"
        qu.intent = "general_explanation"
        qu.required_information = "overview, architecture, and core features of the framework"
        qu.search_query_optimized = f"{qu.primary_entity} framework overview definition"

    # Movies
    elif qu.entity_type == "media" or (any(re.search(p, q_lower) for p in RECOMMENDATION_PATTERNS) and "movie" in q_lower):
        qu.topic = "movies"
        qu.intent = "recommendation"
        qu.recommendation_requirement = True
        qu.required_information = "movie recommendations, ratings, and notable releases"
        if "2026" in q_lower:
            qu.search_query_optimized = "best movies in 2026 top rated film releases"
        elif "2027" in q_lower:
            qu.search_query_optimized = "upcoming movies in 2027 releases"

    # AI News / Live News
    elif any(re.search(p, q_lower) for p in [r"\b(what happened in.*today|ai news|news today|happening in.*now)\b"]):
        qu.topic = "news"
        qu.intent = "live_update"
        qu.required_information = "latest news developments and events"
        qu.search_query_optimized = "latest AI news developments today 2026"

    # Fallback search query
    if not qu.search_query_optimized:
        qu.search_query_optimized = q_clean

    return qu


def _evaluate_action_branch(
    q_text: str,
    q_lower: str,
    attachments: List[Dict[str, Any]],
    memory_data: Optional[Dict[str, Any]],
    task_type: Optional[str],
    is_coding: bool,
    has_image: bool,
    qu: QueryUnderstanding
) -> ActionDecision:
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

    # 2. Personal Memory / Declaration Check (Highest priority before web search to prevent false triggers)
    has_memory_pattern = any(re.search(p, q_lower) for p in MEMORY_PATTERNS) or is_personal_memory_statement(q_text)
    # Only treat as memory recall if NOT an external search request
    if has_memory_pattern and not any(re.search(p, q_lower) for p in EXPLICIT_SEARCH_PATTERNS[:1]):
        return ActionDecision(
            action=ACTION_MEMORY_RECALL,
            reason="User asked a question or shared a statement about personal identity, project, or conversation context.",
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

    # 3. Explicit Verification Check
    verify_patterns = [
        r"\b(verify|confirm|check whether|check if)\b",
        r"\bis this correct\b",
        r"\bis this true\b",
        r"\bgive me verified\b"
    ]
    is_verification = any(re.search(pat, q_lower) for pat in verify_patterns)
    if is_verification:
        return ActionDecision(
            action=ACTION_WEB_SEARCH,
            reason="User explicitly requested factual verification or statement checking.",
            confidence=0.98,
            requires_world_access=True,
            requires_fresh_information=True,
            query_intent="verification",
            task_type="verification_request",
            information_need="official_entity_evidence",
            priority="high",
            freshness_requirement=FRESHNESS_CURRENT,
            planned_actions=[ACTION_WEB_SEARCH, ACTION_LOCAL_REASONING]
        )

    # 4. Browser Interact Check
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

    # 5. Browser Read Check
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

    # 6. Explicit Web Fetch (URL) Check
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

    # 7. Deep Web Research Check (Multi-source comparison)
    if any(re.search(p, q_lower) for p in DEEP_RESEARCH_PATTERNS) and any(w in q_lower for w in ["latest", "current", "compare", "models", "options", "sources", "2026"]):
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

    # 8. Local Information, Regional Discovery & Recommendation Queries
    if is_local_or_recommendation_query(q_text):
        return ActionDecision(
            action=ACTION_WEB_SEARCH,
            reason="Local information, regional heritage, or current recommendations requested. Web grounding required.",
            confidence=0.96,
            requires_world_access=True,
            requires_fresh_information=True,
            query_intent="local_and_recommendation_discovery",
            task_type="information_request",
            information_need="local_and_recommendation_evidence",
            priority="high",
            freshness_requirement=FRESHNESS_CURRENT,
            planned_actions=[ACTION_WEB_SEARCH, ACTION_LOCAL_REASONING]
        )

    # 9. Current / Time-Sensitive / 2026 Web Search Check
    freshness = classify_freshness(q_text)
    is_fresh_search = freshness in [FRESHNESS_USER_EXPLICIT_SEARCH, FRESHNESS_CURRENT, FRESHNESS_CURRENT_EXTERNAL_FACT, FRESHNESS_LIVE] or any(re.search(p, q_lower) for p in EXPLICIT_SEARCH_PATTERNS)
    
    if is_fresh_search:
        # CURRENT_EXTERNAL_FACT gets higher priority and distinct intent
        is_cef = (freshness == FRESHNESS_CURRENT_EXTERNAL_FACT)
        return ActionDecision(
            action=ACTION_WEB_SEARCH,
            reason="CURRENT_EXTERNAL_FACT: Query requires real external evidence for current version/release information. Model pretrained knowledge is NOT sufficient." if is_cef else "Request requires fresh, current, or time-sensitive public information (operating year: 2026).",
            confidence=0.98 if is_cef else 0.95,
            requires_world_access=True,
            requires_fresh_information=True,
            query_intent="current_external_fact" if is_cef else "current_information",
            task_type="current_external_fact" if is_cef else "information_request",
            information_need="current_version_release_evidence" if is_cef else "latest_public_data",
            priority="high" if is_cef else "normal",
            freshness_requirement=freshness,
            planned_actions=[ACTION_WEB_SEARCH, ACTION_LOCAL_REASONING]
        )

    # 10. RAG / Local Document Check
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

    # 11. Coding / Programming Check (Pure coding tasks without latest version queries)
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

    # 12. Ambiguous / Low Confidence Check
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

    # 13. Default: Local Reasoning (Static General Knowledge & Casual Banter)
    return ActionDecision(
        action=ACTION_LOCAL_REASONING,
        reason="Standard conversational or static general knowledge query processed via local intelligence.",
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
    Sprint 1: Authoritative date-aware (August 2026) & local/recommendation intent classification.
    Sprint 5: Structured QueryUnderstanding with Entity & Location Separation.
    """
    try:
        q_text = (query or "").strip()
        q_lower = q_text.lower()
        attachments = attachments or []
        qu = parse_query_understanding(q_text)

        decision = _evaluate_action_branch(
            q_text=q_text,
            q_lower=q_lower,
            attachments=attachments,
            memory_data=memory_data,
            task_type=task_type,
            is_coding=is_coding,
            has_image=has_image,
            qu=qu
        )
        decision.query_understanding = qu
        return decision

    except Exception as e:
        # Fallback safety net — never crash the system
        qu = parse_query_understanding(query or "")
        return ActionDecision(
            action=ACTION_LOCAL_REASONING,
            reason=f"Action engine error fallback: {str(e)}",
            confidence=0.50,
            requires_world_access=False,
            requires_fresh_information=False,
            fallback_action=ACTION_LOCAL_REASONING,
            decision_status="FALLBACK",
            query_understanding=qu
        )
