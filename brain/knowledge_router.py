from typing import List, Dict, Any
from brain.schemas import RouteResult

def route_request(
    query: str, 
    intent: str, 
    urls: List[str] = None,
    attachments: List[Dict[str, Any]] = None
) -> RouteResult:
    """
    Decides which information sources to query to satisfy the request.
    Possible sources: Memory, Knowledge DB, Browser, Project Docs, GitHub, User Profile, LLM
    """
    urls = urls or []
    attachments = attachments or []
    
    query_lower = query.lower()
    sources = []
    
    # 1. Memory Route (past conversations)
    memory_keywords = {"remember", "forget", "recall", "past conversation", "what did i say", "remind me", "our last chat"}
    if intent == "Memory" or any(kw in query_lower for kw in memory_keywords):
        sources.append("Memory")
        
    # 2. Browser Route (web search, news, current events)
    browser_keywords = {"weather", "price of", "stock", "news", "today", "latest", "current", "release date of", "who is the current"}
    if intent in ["News", "Current Events"] or any(kw in query_lower for kw in browser_keywords):
        sources.append("Browser")
        
    # 3. GitHub Route
    github_keywords = {"github", "gist.github", "github repo", "pull request", "commit history"}
    if any(kw in query_lower for kw in github_keywords) or any("github.com" in url.lower() for url in urls):
        sources.append("GitHub")
        
    # 4. Project Docs Route (workspace intelligence)
    project_keywords = {"workspace", "repository", "codebase", "folder structure", "project files", "readme", "active directory"}
    if intent == "Project" or any(kw in query_lower for kw in project_keywords):
        sources.append("Project Docs")
        
    # 5. User Profile Route (personal preferences)
    profile_keywords = {"my name", "my preferences", "who am i", "my settings", "profile", "my birthday", "where do i live"}
    if any(kw in query_lower for kw in profile_keywords):
        sources.append("User Profile")
        
    # 6. Knowledge DB / Vector DB (general reference, tutorials)
    knowledge_keywords = {"tutorial", "how does", "explain to a beginner", "documentation of", "history of", "science", "math"}
    if intent in ["Learning", "Research", "Math"] or any(kw in query_lower for kw in knowledge_keywords) or len(attachments) > 0:
        sources.append("Knowledge DB")
        
    # 7. LLM Route (standard generator fallback, always appended if not present)
    # LLM is usually the final synthesizer
    sources.append("LLM")
    
    # Clean duplicates but preserve order
    unique_sources = []
    for src in sources:
        if src not in unique_sources:
            unique_sources.append(src)
            
    # If no specific route is determined, route to LLM and general knowledge
    if len(unique_sources) == 1 and "LLM" in unique_sources:
        unique_sources = ["Knowledge DB", "LLM"]
        
    # Lowercase match of output from ticket requirement if needed:
    # "route": ["browser", "knowledge"]
    # Let's map our internal source names to lowercased outputs to match the ticket spec.
    # Map internal names to match:
    # Memory -> memory
    # Knowledge DB -> knowledge (or knowledge_db)
    # Browser -> browser
    # Project Docs -> project_docs
    # GitHub -> github
    # User Profile -> user_profile
    # LLM -> llm
    map_names = {
        "Memory": "memory",
        "Knowledge DB": "knowledge",
        "Browser": "browser",
        "Project Docs": "project_docs",
        "GitHub": "github",
        "User Profile": "user_profile",
        "LLM": "llm"
    }
    
    mapped_sources = [map_names[src] for src in unique_sources if src in map_names]
    
    return RouteResult(route=mapped_sources)
