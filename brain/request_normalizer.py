import uuid
from datetime import datetime, timezone
import re
from typing import List, Dict, Any

from brain.schemas import RequestInput, NormalizedRequest
from brain.utils.text import clean_and_normalize, detect_markdown
from brain.language_detector import detect_language

# A robust URL extraction regex
URL_PATTERN = re.compile(
    r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
)

def extract_urls(text: str) -> List[str]:
    """Extract all unique URLs from text while preserving their order."""
    if not text:
        return []
    
    matches = URL_PATTERN.findall(text)
    
    # Remove duplicates but maintain order
    seen = set()
    unique_urls = []
    for url in matches:
        # Strip trailing common trailing punctuation that might be caught
        cleaned_url = url.rstrip('.,;?!)(')
        if cleaned_url not in seen:
            seen.add(cleaned_url)
            unique_urls.append(cleaned_url)
            
    return unique_urls

def normalize_request(request_in: RequestInput) -> NormalizedRequest:
    """
    Main entry point for request normalization.
    Converts a raw RequestInput to a structured NormalizedRequest.
    """
    raw_message = request_in.message or ""
    
    # 1. Clean and normalize query text
    clean_query = clean_and_normalize(raw_message)
    
    # 2. Extract URLs
    urls = extract_urls(raw_message)
    
    # 3. Detect markdown
    is_md = detect_markdown(raw_message)
    
    # 4. Generate UUID request ID
    req_id = str(uuid.uuid4())
    
    # 5. Get current ISO 8601 UTC timestamp
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 6. Detect language (falls back to 'en' internally)
    lang_info = detect_language(clean_query)
    
    return NormalizedRequest(
        id=req_id,
        query=clean_query,
        language=lang_info.language,
        urls=urls,
        attachments=request_in.attachments,
        timestamp=timestamp,
        is_markdown=is_md
    )
