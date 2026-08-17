import re

from backend.core.config import settings


SECRET_PATTERNS = [
    r"(?i)\b(api[_ -]?key|apikey|password|passwd|secret|token|bearer|private[_ -]?key)\s*[:=]\s*\S+",
    r"(?i)\b(sk-[a-z0-9_-]{20,})\b",
    r"(?i)\b(authorization|cookie)\s*[:=]\s*\S+",
]

PERSONAL_PATTERNS = [
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    r"\b(?:\+?\d[\d ()-]{8,}\d)\b",
]


def make_safe_query(user_input: str) -> str:
    """Create an outbound query without forwarding secrets or direct personal identifiers.

    Privacy failure is fail-closed: the original user input is never used as a fallback.
    """
    text = (user_input or "").strip()
    if not text:
        return ""

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            return ""

    sanitized = text
    for pattern in PERSONAL_PATTERNS:
        sanitized = re.sub(pattern, "", sanitized)

    sanitized = re.sub(r"\s+", " ", sanitized).strip(" ,.;:-")

    if str(settings.PRIVACY_MODE).upper() == "HIGH":
        # HIGH mode is intentionally conservative: callers should use the native
        # World Access manager, which can classify the request before networking.
        return sanitized

    return sanitized


def expand_query(query: str) -> list[str]:
    """Deterministically create small search variants without sending the query to an LLM."""
    clean = " ".join((query or "").split()).strip()
    if not clean:
        return []

    parts = [p.strip() for p in re.split(r"\s+(?:and|vs|versus)\s+", clean, flags=re.IGNORECASE) if p.strip()]
    if len(parts) > 1:
        return [clean, parts[0]]
    return [clean]
