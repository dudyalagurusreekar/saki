import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from brain.schemas import ContextItem, ContextResult

def calculate_overlap_score(content: str, query: str) -> float:
    """Calculate Jaccard similarity score between content and query words."""
    if not content or not query:
        return 0.0
        
    content_words = set(re.findall(r'\w+', content.lower()))
    query_words = set(re.findall(r'\w+', query.lower()))
    
    if not query_words:
        return 0.0
        
    intersection = content_words.intersection(query_words)
    union = content_words.union(query_words)
    
    # Standard overlap score
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # We map this to a score between 0.1 and 1.0 (so there's always a baseline)
    return round(0.1 + (jaccard * 0.9), 2)

def build_context(
    query: str,
    raw_items: List[Dict[str, Any]],
    token_budget: int = 4000
) -> ContextResult:
    """
    Assembles, de-duplicates, ranks, and compresses context items.
    
    Each raw item should look like:
    {
      "source": "memory" | "browser" | "project_docs" | "knowledge" | "user_profile",
      "content": "...",
      "timestamp": "2026-06-26T23:00:00Z" (optional),
      "citation": "..." (optional)
    }
    """
    # Character limit estimation: 1 token ~= 4 characters
    char_limit = token_budget * 4
    
    # 1. De-duplicate contexts
    seen_contents = set()
    unique_items = []
    
    for item in raw_items:
        content = item.get("content", "").strip()
        if not content:
            continue
            
        # Normalize content for comparison (strip punctuation and collapse whitespace)
        norm_content = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', content.lower())).strip()
        
        # Check for duplication (exact or extremely high similarity prefix)
        if norm_content not in seen_contents:
            seen_contents.add(norm_content)
            unique_items.append(item)
            
    # 2. Score and rank relevance
    scored_items = []
    for item in unique_items:
        content = item.get("content", "")
        source = item.get("source", "knowledge")
        citation = item.get("citation") or f"{source}_source"
        
        # Base Jaccard relevance score
        rel_score = calculate_overlap_score(content, query)
        
        # Source importance adjustments
        source_bias = {
            "user_profile": 0.1,
            "memory": 0.05,
            "project_docs": 0.05,
            "browser": 0.0,
            "knowledge": -0.05
        }
        
        score = min(1.0, max(0.0, rel_score + source_bias.get(source, 0.0)))
        
        scored_items.append({
            "item": item,
            "score": score,
            "citation": citation
        })
        
    # Sort items: primary sort by relevance score descending, 
    # secondary sort by chronology (if timestamp available, older first, or preserve original index)
    def sort_key(x):
        ts_str = x["item"].get("timestamp")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                return (-x["score"], dt.timestamp())
            except Exception:
                pass
        return (-x["score"], 0)
        
    scored_items.sort(key=sort_key)
    
    # 3. Compress context within token/character budget
    current_chars = 0
    final_context_items = []
    
    for entry in scored_items:
        item = entry["item"]
        content = item["content"]
        item_len = len(content)
        
        # If adding this item exceeds budget, we can truncate it or drop it.
        # We try to keep it by truncating if it's very important or just drop it.
        if current_chars + item_len <= char_limit:
            final_context_items.append(
                ContextItem(
                    source=item["source"],
                    score=entry["score"],
                    content=content,
                    citation=entry["citation"]
                )
            )
            current_chars += item_len
        else:
            # Add remaining room portion if it has at least 100 characters of space
            remaining_room = char_limit - current_chars
            if remaining_room > 100:
                truncated_content = content[:remaining_room] + "... [truncated]"
                final_context_items.append(
                    ContextItem(
                        source=item["source"],
                        score=entry["score"],
                        content=truncated_content,
                        citation=entry["citation"]
                    )
                )
                current_chars += len(truncated_content)
            break
            
    return ContextResult(context=final_context_items)
