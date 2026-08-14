from typing import List, Dict, Any
from brain.schemas import ComplexityResult

def analyze_complexity(
    query: str, 
    intent: str, 
    urls: List[str] = None, 
    attachments: List[Dict[str, Any]] = None
) -> ComplexityResult:
    """
    Analyzes query characteristics to estimate complexity and required steps.
    """
    urls = urls or []
    attachments = attachments or []
    
    query_len = len(query)
    word_count = len(query.split())
    
    # 1. Base rules scoring system
    score = 0
    
    # Text length contributions
    if word_count > 40:
        score += 4
    elif word_count > 20:
        score += 2
    elif word_count > 10:
        score += 1
        
    # URL counts contributions
    score += len(urls) * 2
    
    # Attachment contributions
    for att in attachments:
        att_type = att.get("type", "").lower()
        if att_type in ["pdf", "docx", "zip"]:
            score += 4 # Heavy files
        else:
            score += 2 # Standard files (txt, csv, image)
            
    # Intent profile contributions
    intent_complexity_map = {
        "Casual Chat": 1,
        "Translation": 1,
        "Memory": 2,
        "Math": 3,
        "Writing": 3,
        "Current Events": 3,
        "News": 3,
        "Learning": 4,
        "Vision": 4,
        "Image Generation": 4,
        "Coding": 5,
        "Debugging": 5,
        "Project": 6,
        "Planning": 6,
        "Research": 7
    }
    
    intent_score = intent_complexity_map.get(intent, 2)
    score += intent_score
    
    # Specific terms requesting long/heavy work
    long_running_keywords = {"overnight", "scrape all", "benchmark", "full audit", "crawl", "train", "deep scan"}
    if any(kw in query.lower() for kw in long_running_keywords):
        score += 8
        
    # 2. Map score to complexity and estimated steps
    if score >= 14:
        complexity = "Long Running"
        steps = max(13, min(20, score))
    elif score >= 9:
        complexity = "Research"
        steps = max(9, min(12, score))
    elif score >= 6:
        complexity = "Complex"
        steps = max(6, min(8, score))
    elif score >= 3:
        complexity = "Medium"
        steps = max(3, min(5, score))
    else:
        complexity = "Simple"
        steps = max(1, min(2, score))
        
    return ComplexityResult(
        complexity=complexity,
        estimated_steps=steps
    )
