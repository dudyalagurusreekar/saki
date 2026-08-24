import uuid
from datetime import datetime, timezone
import re
from typing import List, Dict, Any, Union
from brain.schemas import RequestInput, UnifiedTurnRequest, NormalizedRequest, InputType
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

def normalize_request(request_in: Union[RequestInput, UnifiedTurnRequest, Dict[str, Any]]) -> NormalizedRequest:
    """
    Main entry point for request normalization.
    Converts a raw RequestInput, UnifiedTurnRequest, or dict to a structured NormalizedRequest.
    Preserves input_type, turn_id, voice_metadata, attachments, and contextual metadata.
    """
    if isinstance(request_in, dict):
        raw_message = request_in.get("text") or request_in.get("message") or ""
        attachments = request_in.get("attachments") or []
        turn_id = request_in.get("turn_id") or request_in.get("request_id")
        input_type_val = request_in.get("input_type", InputType.TEXT)
        voice_meta = request_in.get("voice_metadata")
        curr_ctx = request_in.get("current_context") or {}
        lang_hint = request_in.get("language_hint")
        lang_mode = request_in.get("language_mode", "AUTO")
    elif hasattr(request_in, "message") or hasattr(request_in, "text"):
        raw_message = getattr(request_in, "text", None) or getattr(request_in, "message", "") or ""
        attachments = getattr(request_in, "attachments", None) or []
        turn_id = getattr(request_in, "turn_id", None) or getattr(request_in, "request_id", None)
        input_type_val = getattr(request_in, "input_type", InputType.TEXT)
        voice_meta = getattr(request_in, "voice_metadata", None)
        curr_ctx = getattr(request_in, "current_context", None) or {}
        lang_hint = getattr(request_in, "language_hint", None)
        lang_mode = getattr(request_in, "language_mode", "AUTO")
    else:
        raw_message = str(request_in or "")
        attachments = []
        turn_id = None
        input_type_val = InputType.TEXT
        voice_meta = None
        curr_ctx = {}
        lang_hint = None
        lang_mode = "AUTO"

    # Ensure input_type is InputType enum
    if isinstance(input_type_val, str):
        try:
            input_type_enum = InputType(input_type_val.upper())
        except Exception:
            input_type_enum = InputType.TEXT
    else:
        input_type_enum = input_type_val or InputType.TEXT

    # 1. Clean and normalize query text
    clean_query = clean_and_normalize(raw_message)
    
    # 2. Extract URLs
    urls = extract_urls(raw_message)
    
    # 3. Detect markdown
    is_md = detect_markdown(raw_message)
    
    # 4. Generate UUID request ID and preserve turn_id
    req_id = str(uuid.uuid4())
    effective_turn_id = turn_id or f"turn_{req_id[:12]}"
    
    # 5. Get current ISO 8601 UTC timestamp
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 6. Detect language (falls back to caller hint or 'en')
    if lang_hint in ["en", "te", "kn", "hi", "es", "fr", "de"]:
        lang_code = lang_hint
    else:
        lang_info = detect_language(clean_query)
        lang_code = lang_info.language
    
    return NormalizedRequest(
        id=req_id,
        turn_id=effective_turn_id,
        input_type=input_type_enum,
        query=clean_query,
        language=lang_code,
        language_mode=lang_mode or "AUTO",
        urls=urls,
        attachments=attachments,
        voice_metadata=voice_meta,
        current_context=curr_ctx,
        timestamp=timestamp,
        is_markdown=is_md
    )
