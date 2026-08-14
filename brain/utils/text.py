import re
import unicodedata

def normalize_unicode(text: str) -> str:
    """Normalize unicode representation to NFC standard form."""
    if not text:
        return ""
    return unicodedata.normalize("NFC", text)

def remove_invisible_characters(text: str) -> str:
    """Remove control and formatting invisible characters (e.g., zero-width spaces, control codes)."""
    if not text:
        return ""
    # Category Cc is Control, Cf is Format
    clean = "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf"))
    # Explicitly clear common zero-width space characters
    clean = clean.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '').replace('\ufeff', '')
    return clean

def trim_whitespace(text: str) -> str:
    """Trim leading/trailing whitespace and collapse duplicate whitespace characters."""
    if not text:
        return ""
    # Replace multiple spaces/newlines with a single space for normalized queries,
    # but preserve some format if needed. Here we collapse all spacing for standard queries.
    return re.sub(r'\s+', ' ', text).strip()

def clean_and_normalize(text: str) -> str:
    """Run all cleaning steps sequentially."""
    if not text:
        return ""
    text = normalize_unicode(text)
    text = remove_invisible_characters(text)
    text = trim_whitespace(text)
    return text

def detect_markdown(text: str) -> bool:
    """
    Check if the text contains markdown syntax patterns:
    - Headers: # Title
    - Lists: - item, * item, 1. item
    - Bold/Italic: **text**, *text*, _text_
    - Code blocks: ```python or `code`
    - Links: [title](url)
    - Blockquotes: > quote
    """
    if not text:
        return False
    
    patterns = [
        r'^#{1,6}\s+\S+',                    # Headings
        r'^\s*[\-\*\+]\s+\S+',               # Unordered lists
        r'^\s*\d+\.\s+\S+',                  # Ordered lists
        r'\*\*.*?\*\*',                      # Bold
        r'\*.*?\*',                          # Italic
        r'`{3}[\s\S]*?`{3}',                  # Fenced code blocks
        r'`[^`\n]+`',                        # Inline code
        r'\[.*?\]\(.*?\)',                   # Links
        r'^\s*>\s+\S+',                      # Blockquotes
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.MULTILINE):
            return True
            
    return False
