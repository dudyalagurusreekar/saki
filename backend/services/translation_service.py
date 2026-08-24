"""
Saki Stable Translation Pipeline (Core Flow)

Authoritative translation boundary for the unified brain flow:
  1. Detect user language            (multilingual_service)
  2. Translate input -> English      (to_english)     -> routing / memory / generation
  3. Specialist model answers in English (stable chat behavior)
  4. Translate answer -> user language (from_english)
  5. TTS speaks the translated answer

Design guarantees:
- Never raises: every failure degrades gracefully to the original text.
- LRU cache prevents re-translating identical payloads.
- Output validation strips model preambles and rejects junk translations.
- Single fast multilingual model (settings.TRANSLATION_MODEL) is used for both directions.
"""

import re
import time
import threading
from collections import OrderedDict
from typing import Dict, Optional, Tuple

from backend.core.config import settings


# Human-readable names used inside translation prompts
LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "te": "Telugu",
    "kn": "Kannada",
    "hi": "Hindi",
    "ta": "Tamil",
    "mr": "Marathi",
    "bn": "Bengali",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ur": "Urdu",
    "ar": "Arabic",
}

# Preambles models tend to add; stripped before returning translations
_PREAMBLE_PATTERNS = [
    r"^\s*here(?:'s| is) the translation\s*:?\s*",
    r"^\s*translation\s*:?\s*",
    r"^\s*translated(?:\s+text)?\s*:?\s*",
    r"^\s*(?:telugu|kannada|hindi|english)\s*translation\s*:?\s*",
]

# If a translation attempt produces only these, it is treated as failed
_FAILURE_MARKERS = [
    "i cannot translate", "i can't translate", "i am unable to translate",
    "unable to translate", "cannot be translated", "as an ai",
]


def _language_name(lang: str) -> str:
    return LANGUAGE_NAMES.get((lang or "en").lower(), "English")


class TranslationService:
    """
    Deterministic, failure-tolerant translation service for the Saki core flow.
    Uses the local Ollama inference engine through ai_service.call_model.
    """

    CACHE_SIZE = 256
    MIN_TRANSLATABLE_LEN = 2

    def __init__(self):
        self._cache: "OrderedDict[str, str]" = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {
            "to_english_calls": 0,
            "from_english_calls": 0,
            "cache_hits": 0,
            "fallbacks": 0,
        }

    # -------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------
    def needs_translation(self, lang: str) -> bool:
        """True when the given ISO code requires pipeline translation."""
        return bool(lang) and lang.lower() != "en"

    def to_english(self, text: str, source_lang: str = "auto") -> str:
        """
        Translates non-English user input into English so intent classification,
        orchestrator routing, memory retrieval, and generation all operate on
        stable English text (exactly like normal chat).
        Returns the original text unchanged when translation is unnecessary,
        disabled, or fails.
        """
        return self._translate(text=text, source_lang=source_lang, target_lang="en", direction="to_english")

    def from_english(self, text: str, target_lang: str) -> str:
        """
        Translates an English Saki response into the user's language right
        before display / TTS. Returns the English original on any failure.
        """
        return self._translate(text=text, source_lang="en", target_lang=target_lang, direction="from_english")

    def get_stats(self) -> Dict[str, object]:
        with self._lock:
            return dict(self._stats)

    # -------------------------------------------------------------
    # INTERNALS
    # -------------------------------------------------------------
    def _cache_key(self, text: str, target_lang: str) -> str:
        return f"{target_lang.lower()}::{hash(text)}::{len(text)}"

    def _cache_get(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._stats["cache_hits"] += 1
                return self._cache[key]
        return None

    def _cache_put(self, key: str, value: str) -> None:
        with self._lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            while len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)

    def _translate(self, text: str, source_lang: str, target_lang: str, direction: str) -> str:
        if not text or not text.strip():
            return text

        if not getattr(settings, "ENABLE_TRANSLATION", True):
            return text

        # Same-language short-circuit (nothing to do)
        src = (source_lang or "auto").lower()
        tgt = (target_lang or "en").lower()
        if src == tgt:
            return text

        target_name = _language_name(target_lang)

        # Text already in target script/language → skip work.
        if self._already_in_target_language(text, target_lang):
            return text

        key = self._cache_key(text, target_lang)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        with self._lock:
            self._stats[direction] = self._stats.get(direction, 0) + 1

        system_prompt = (
            "You are a precise real-time translator engine.\n"
            "Rules:\n"
            f"- Translate the user's message into {target_name}.\n"
            "- Preserve meaning, tone, emotion, and intent exactly.\n"
            "- Keep programming code, code identifiers, framework names, URLs, file paths, "
            "numbers, and technical terms (Python, FastAPI, React, API, HTTP) in English.\n"
            f"- Use natural everyday conversational {target_name}, NOT formal textbook style.\n"
            "- Output ONLY the translation. No preamble, no quotes, no explanation."
        )

        try:
            from backend.core.saki_persona import format_prompt_for_model
            model_name = getattr(settings, "TRANSLATION_MODEL", settings.MODEL_GEMMA)
            prompt = format_prompt_for_model(model_name, system_prompt, text.strip())
        except Exception:
            model_name = getattr(settings, "TRANSLATION_MODEL", settings.MODEL_GEMMA)
            prompt = (
                f"{system_prompt}\n\n"
                f"Translate into {target_name}:\n{text.strip()}\n"
                f"{target_name} translation:"
            )

        raw = self._call_translation_model(prompt, model_name)

        translated = self._validate(raw, text)
        if translated is None:
            with self._lock:
                self._stats["fallbacks"] += 1
            return text  # graceful degradation: never break the core flow

        self._cache_put(key, translated)
        return translated

    def _call_translation_model(self, prompt: str, model_name: str) -> str:
        """Single guarded call to the local translation model."""
        try:
            from backend.services.ai_service import call_model
            started = time.perf_counter()
            result = call_model(
                prompt,
                model=model_name,
                keep_alive=settings.MODEL_KEEP_ALIVE_SESSION
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            print(f"[Translation] '{model_name}' responded in {latency_ms:.0f} ms")
            return result or ""
        except Exception as exc:
            print(f"[Translation Non-Fatal Error]: {exc}")
            return ""

    @staticmethod
    def _already_in_target_language(text: str, target_lang: str) -> bool:
        """Script shortcut: native-script text cannot already be English."""
        if not text:
            return False
        sample = text[:400]
        if target_lang == "te":
            return bool(re.search(r"[\u0C00-\u0C7F]", sample)) and not re.search(r"[a-zA-Z]{4,}", sample)
        if target_lang == "kn":
            return bool(re.search(r"[\u0C80-\u0CFF]", sample)) and not re.search(r"[a-zA-Z]{4,}", sample)
        if target_lang == "hi":
            return bool(re.search(r"[\u0900-\u097F]", sample)) and not re.search(r"[a-zA-Z]{4,}", sample)
        return False

    def _validate(self, raw: str, original: str) -> Optional[str]:
        """
        Cleans and validates a raw model translation.
        Returns None when the output is unusable so callers fall back safely.
        """
        if not raw:
            return None

        out = raw.strip().strip('"').strip("'").strip()
        out = out.replace("**", "")

        for pattern in _PREAMBLE_PATTERNS:
            out = re.sub(pattern, "", out, flags=re.IGNORECASE).strip()

        if not out or len(out) < self.MIN_TRANSLATABLE_LEN:
            return None

        lowered = out.lower()
        if any(marker in lowered for marker in _FAILURE_MARKERS):
            return None

        # Reject degenerate label-only answers like "Telugu:" / "English translation:"
        if re.fullmatch(r"[A-Za-z ]{1,20}:", out):
            return None

        # Reject degenerate repetition of the exact English original for non-English targets
        if out.strip() == original.strip():
            return None

        return out


# Global singleton
translation_service = TranslationService()
