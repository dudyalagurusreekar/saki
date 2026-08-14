import re
from urllib.parse import urlparse
from typing import List, Dict, Any

from brain.schemas import URLClassification

# Reuse the robust URL regex pattern
URL_PATTERN = re.compile(
    r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
)

def classify_url(url: str) -> URLClassification:
    """
    Parse and classify a single URL into one of the categories:
    github, youtube, docs, wikipedia, pdf, blog.
    """
    # Clean trailing punctuation
    cleaned_url = url.rstrip('.,;?!)(')
    
    # 1. Parse domain
    try:
        parsed = urlparse(cleaned_url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            domain = netloc[4:]
        else:
            domain = netloc
        path = parsed.path.lower()
    except Exception:
        domain = "unknown"
        path = ""
        
    # 2. Classification logic
    category = "blog" # Default fallback
    
    if "github.com" in domain or "gist.github.com" in domain:
        category = "github"
    elif "youtube.com" in domain or "youtu.be" in domain:
        category = "youtube"
    elif "wikipedia.org" in domain:
        category = "wikipedia"
    elif path.endswith(".pdf") or ".pdf" in cleaned_url.lower():
        category = "pdf"
    elif (
        "docs.google.com" in domain or 
        "docs." in domain or 
        "readthedocs" in domain or 
        "documentation" in domain or 
        "docs" in path or 
        "wiki" in path or
        "documentation" in path
    ):
        category = "docs"
        
    return URLClassification(
        url=cleaned_url,
        domain=domain or "unknown",
        category=category
    )

def analyze_urls(text: str) -> List[URLClassification]:
    """Extract, de-duplicate, and classify all URLs in a given text."""
    if not text:
        return []
        
    matches = URL_PATTERN.findall(text)
    
    seen = set()
    classifications = []
    
    for url in matches:
        cleaned_url = url.rstrip('.,;?!)(')
        if cleaned_url not in seen:
            seen.add(cleaned_url)
            classifications.append(classify_url(cleaned_url))
            
    return classifications
