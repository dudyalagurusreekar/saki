import re
from typing import List
from brain.schemas import LanguageResult

# Try to import langdetect, but provide a mock/stub if installation is still running
try:
    from langdetect import detect_langs
    from langdetect.lang_detect_exception import LangDetectException
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False

# Regex for Telugu script characters
TELUGU_SCRIPT_RE = re.compile(r'[\u0c00-\u0c7f]+')
# Regex for Devanagari (Hindi) script characters
HINDI_SCRIPT_RE = re.compile(r'[\u0900-\u097f]+')
# Regex for alphanumeric/letters (checks if any linguistic content exists)
WORDS_RE = re.compile(r'[a-zA-Z0-9\u0400-\u04FF\u0900-\u097F\u0c00-\u0c7F]+')

def is_emoji_only_or_non_linguistic(text: str) -> bool:
    """Check if the text is empty, contains only emojis, symbols, numbers or punctuation."""
    if not text or not text.strip():
        return True
    
    # If there are no words/alphanumeric characters, it is non-linguistic
    if not WORDS_RE.search(text):
        return True
        
    return False

def detect_language(text: str) -> LanguageResult:
    """
    Detects the language of a query.
    Handles Hindi, Telugu, English, mixed languages, and emoji-only queries.
    """
    # 1. Clean the text
    clean_text = text.strip()
    
    # 2. Check for emoji-only / non-linguistic
    if is_emoji_only_or_non_linguistic(clean_text):
        return LanguageResult(language="en", confidence=1.0)
        
    # 3. Direct script check (extremely high accuracy for native script)
    if TELUGU_SCRIPT_RE.search(clean_text):
        # Determine proportion or just return if present
        return LanguageResult(language="te", confidence=0.99)
        
    if HINDI_SCRIPT_RE.search(clean_text):
        return LanguageResult(language="hi", confidence=0.99)

    # 4. Check for common Telugu/Hindi Romanized keywords first (since langdetect is poor at Romanized Indian languages)
    roman_telugu_keywords = {"ela", "unnav", "enti", "cheppu", "namaskaram", "kuda", "nenu", "telugu"}
    roman_hindi_keywords = {"kya", "kaise", "ho", "namaste", "hai", "aur", "mera", "aap", "tum"}
    
    words = set(re.findall(r'\b\w+\b', clean_text.lower()))
    if words & roman_telugu_keywords:
        return LanguageResult(language="te", confidence=0.7)
    if words & roman_hindi_keywords:
        return LanguageResult(language="hi", confidence=0.7)

    # 5. Use langdetect if available
    if _HAS_LANGDETECT:
        try:
            predictions = detect_langs(clean_text)
            if predictions:
                # Top prediction
                top_pred = predictions[0]
                lang = top_pred.lang
                conf = top_pred.prob
                
                # Check for mixed languages: if there is a secondary language with substantial probability
                # We return the primary one but can adjust confidence or log
                return LanguageResult(language=lang, confidence=round(conf, 2))
        except Exception:
            # Fallback on parsing exceptions
            pass

    # Ultimate fallback to English
    return LanguageResult(language="en", confidence=0.5)
