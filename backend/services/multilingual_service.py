"""
Saki Multilingual Intelligence Subsystem (Sprint 3)
Provides deterministic script classification, code-mixing detection, multilingual text
normalization, phonetic transcription, explicit language request handling, and cross-lingual
semantic keyword mapping for English, Telugu (తెలుగు), Kannada (ಕನ್ನಡ), and mixed-language conversation.
Operates 100% locally with zero cloud API dependencies.
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field


@dataclass
class LanguageProfile:
    language: str = "en"                      # "en", "te", "kn", "mixed", "unknown"
    primary_language: str = "en"              # "en", "te", "kn", "unknown"
    secondary_language: Optional[str] = None  # "en", "te", "kn", or None
    is_mixed: bool = False                    # Backward compatibility alias for is_code_mixed
    is_code_mixed: bool = False               # True if code-mixed (e.g. te+en, kn+en)
    confidence: float = 1.0                   # Detection confidence score 0.0 - 1.0
    mode: str = "pure_en"                     # "pure_en", "pure_te", "pure_kn", "te+en", "kn+en", "mixed"
    indic_script: Optional[str] = None        # "telugu", "kannada", or None
    telugu_ratio: float = 0.0
    kannada_ratio: float = 0.0
    english_ratio: float = 1.0
    language_label: str = "English"           # Human-readable UI label
    english_terms: List[str] = field(default_factory=list)
    mixed_terms: List[str] = field(default_factory=list)
    language_segments: List[Dict[str, Any]] = field(default_factory=list)
    detection_source: str = "unicode_script"  # "unicode_script", "romanized_lexicon", "stt_hint", "conversation_context", "manual_override", "fallback"
    requested_output_language: Optional[str] = None
    manual_mode: Optional[str] = "AUTO"

    def __post_init__(self):
        if not self.primary_language:
            self.primary_language = self.language if self.language in ["en", "te", "kn"] else "en"
        if self.is_code_mixed and not self.is_mixed:
            self.is_mixed = True
        elif self.is_mixed and not self.is_code_mixed:
            self.is_code_mixed = True
        if not self.mixed_terms and self.english_terms:
            self.mixed_terms = list(self.english_terms)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "primary_language": self.primary_language,
            "secondary_language": self.secondary_language,
            "is_mixed": self.is_mixed or self.is_code_mixed,
            "is_code_mixed": self.is_code_mixed or self.is_mixed,
            "confidence": round(self.confidence, 3),
            "mode": self.mode,
            "indic_script": self.indic_script,
            "telugu_ratio": round(self.telugu_ratio, 3),
            "kannada_ratio": round(self.kannada_ratio, 3),
            "english_ratio": round(self.english_ratio, 3),
            "language_label": self.language_label,
            "english_terms": self.english_terms,
            "mixed_terms": self.mixed_terms,
            "language_segments": self.language_segments,
            "detection_source": self.detection_source,
            "requested_output_language": self.requested_output_language,
            "manual_mode": self.manual_mode
        }


class MultilingualService:
    """
    Core multilingual engine for Saki.
    Handles script detection, code-mixing analysis, Indic pronunciation normalization,
    explicit response language requests, and cross-lingual memory keyword expansion.
    """

    # Unicode Ranges
    TELUGU_RANGE = r'[\u0C00-\u0C7F]'
    KANNADA_RANGE = r'[\u0C80-\u0CFF]'
    LATIN_RANGE = r'[a-zA-Z]'

    # Cross-lingual keyword dictionary for semantic memory retrieval
    CROSS_LINGUAL_SYNONYMS: Dict[str, Set[str]] = {
        "python": {"python", "పైథాన్", "ಪೈಥಾನ್"},
        "javascript": {"javascript", "js", "జావాస్క్రిప్ట్", "ಜಾವಾಸ್ಕ್ರಿಪ್ಟ್"},
        "typescript": {"typescript", "ts", "టైప్‌స్క్రిప్ట్", "ಟೈಪ್‌ಸ್ಕ್ರಿಪ್ಟ್"},
        "fastapi": {"fastapi", "ఫాస్ట్ ఎపిఐ", "ఫాస్టేపిఐ", "ಫಾಸ್ಟ್‌ ಎಪಿಐ"},
        "react": {"react", "రియాక్ట్", "ರಿಯಾಕ್ಟ್"},
        "nextjs": {"nextjs", "next.js", "నెక్స్ట్ జెఎస్", "నెక్స్ట్ ಜೆಎಸ್"},
        "database": {"database", "db", "డేటాబేస్", "డెటాబేస్", "ಡೇಟಾಬೇಸ್"},
        "docker": {"docker", "డాకర్", "ಡಾಕರ್"},
        "project": {"project", "ప్రాజెక్ట్", "ప్రాజెక్టు", "ప్రాజెక్ట్ లు", "ಪ್ರಾಜೆಕ್ಟ್", "ಯೋಜನೆ"},
        "preference": {"preference", "favorite", "like", "love", "ఇష్టం", "అభిరుచి", "ఇష్టమైన", "ಇಷ್ಟ", "ಮೆಚ್ಚಿನ", "ಪ್ರಿಯವಾದ"},
        "language": {"language", "భాష", "భాషలు", "ಭಾಷೆ", "ಭಾಷೆಗಳು"},
        "food": {"food", "dishes", "భోజనం", "ఆహారం", "తిండి", "ಊಟ", "ಆಹಾರ"},
        "coffee": {"coffee", "tea", "కాఫీ", "టీ", "చాయ్", "ಕಾಫಿ", "ಟೀ", "ಚಹಾ"},
        "dark_mode": {"dark mode", "theme", "డార్క్ మోడ్", "థీమ్", "నలుపు థీమ్", "ಡಾರ್ಕ್ ಮೋಡ್", "ಥೀಮ್"},
        "goal": {"goal", "ambition", "target", "లక్ష్యం", "గురి", "ఆశయం", "ಗುರಿ", "ಧ್ಯೇಯ", "ಉದ್ದೇಶ"},
        "bug": {"bug", "error", "issue", "problem", "లోపం", "బగ్", "సమస్య", "దోషం", "ದೋಷ", "ಬಗ್", "ಸಮಸ್ಯೆ"},
        "name": {"name", "పేరు", "నా పేరు", "ಹೆಸರು", "ನನ್ನ ಹೆಸರು"},
        "city": {"city", "location", "place", "నగరం", "ఊరు", "స్థలం", "నగర", "ಊರು", "ಸ್ಥಳ"},
        "company": {"company", "workplace", "ఆఫీస్", "కంపెనీ", "ఉద్యోగం", "ಕಂಪನಿ", "ಕಚೇರಿ", "ಉದ್ಯೋಗ"},
        "experience": {"experience", "years", "అనుభవం", "సంవత్సరాలు", "ಅನುಭವ", "ವರ್ಷಗಳು"}
    }

    # Explicit Language Request Patterns
    EXPLICIT_ENGLISH_PATTERNS = [
        r"\b(?:in|into|speak|talk|reply|respond|answer|explain|tell me in)\s+english\b",
        r"\b(?:english\s+lo|english\s+lo\s+cheppu|english\s+nalli|english\s+alli|english\s+dalli|english\s+matladu)\b",
        r"\b(?:ఇంగ్లీష్\s*లో|ఆంగ్లంలో|ఇంగ్లీషులో|ఇంగ్లిష్ లో)\b",
        r"\b(?:ಇಂಗ್ಲಿಷ್\s*ನಲ್ಲಿ|ಇಂಗ್ಲಿಷ್\s*ನಲ್ಲಿ\s*ಹೇಳಿ)\b"
    ]

    EXPLICIT_TELUGU_PATTERNS = [
        r"\b(?:in|into|speak|talk|reply|respond|answer|explain|tell me in)\s+telugu\b",
        r"\b(?:telugu\s+lo|telugulo|telugu\s+lo\s+cheppu|telugulo\s+cheppu|telugu\s+matladu|telugulo\s+matladu)\b",
        r"\b(?:తెలుగులో|తెలుగు లో|తెలుగులొ|తెలుగులో\s*(?:చెప్పు|వివరించండి|మాట్లాడు))\b"
    ]

    EXPLICIT_KANNADA_PATTERNS = [
        r"\b(?:in|into|speak|talk|reply|respond|answer|explain|tell me in)\s+kannada\b",
        r"\b(?:kannada\s+dalli|kannadadalli|kannada\s+alli|kannada\s+lo\s+cheppu|kannada\s+nalli|kannada\s+mathadu|kannada\s+heli)\b",
        r"\b(?:ಕನ್ನಡದಲ್ಲಿ|ಕನ್ನಡ ದಲ್ಲಿ|ಕನ್ನಡದಲ್ಲಿ\s*(?:ಹೇಳಿ|ವಿವರಿಸಿ|ಮಾತನಾಡಿ))\b"
    ]

    # Romanized Telugu common vocabulary for phonetic/transliterated Telugu detection
    ROMANIZED_TELUGU_WORDS: Set[str] = {
        "ela", "elaga", "unnav", "unnavu", "unnaru", "unnara", "unnamu", "unnanu",
        "namaskaram", "namaste", "bagunnanu", "bagundi", "bagunnara", "bagane", "baga",
        "ledu", "lede", "kavali", "vaddu", "cheppu", "cheppandi", "cheddam", "cheyali",
        "cheyandi", "enduku", "vastundi", "em", "emi", "enti", "entandi", "eppudu",
        "ekkada", "evuru", "evaru", "naaku", "maaku", "meeku", "neeku", "nenu", "memu",
        "meeru", "nuvvu", "chala", "kastam", "istam", "ishttam", "roju", "dina", "bhasha",
        "dhanyavadalu", "avunu", "kaadu", "undhi", "undi", "chudu", "chudandi", "cheppuko",
        "telugu", "telugulo", "matladu", "matladandi", "sahayam", "cheyi", "chesava",
        "chustunnav", "chestunnav", "tinnava", "paduko", "kada", "kadha", "andi",
        "annai", "garu", "ra", "re"
    }

    # Romanized Kannada common vocabulary for phonetic/transliterated Kannada detection
    ROMANIZED_KANNADA_WORDS: Set[str] = {
        "hege", "iddira", "iddene", "iddiya", "namaskara", "namaste", "chennagiddini",
        "chennagide", "chennagi", "beku", "beda", "heli", "helu", "madona", "madabeku",
        "madi", "yake", "enu", "yavaga", "elli", "yaru", "nanage", "namage", "nimage",
        "ninage", "nanu", "navu", "neevu", "neenu", "tumba", "kasta", "ishta", "dina",
        "bhashe", "dhanyavadagalu", "houdu", "illa", "ide", "nodi", "kannada", "kannadadalli",
        "mathadi", "mathadu", "sahaya", "madu", "madidya", "oota", "aytha"
    }

    @classmethod
    def extract_language_segments(cls, text: str, primary_lang: str = "en") -> List[Dict[str, Any]]:
        """
        Segments code-mixed text into tagged linguistic segments.
        Preserves original ordering, punctuation, and loanwords.
        """
        if not text or not text.strip():
            return []

        tokens = re.findall(r'[^\s]+|\s+', text)
        segments: List[Dict[str, Any]] = []

        current_segment_text = []
        current_lang: Optional[str] = None

        for tok in tokens:
            if not tok.strip():
                # Whitespace belongs to current segment
                if current_segment_text:
                    current_segment_text.append(tok)
                continue

            # Determine token language
            if re.search(cls.TELUGU_RANGE, tok):
                tok_lang = "te"
            elif re.search(cls.KANNADA_RANGE, tok):
                tok_lang = "kn"
            else:
                tok_lower = tok.lower().strip(".,!?:;\"'()")
                if tok_lower in cls.ROMANIZED_TELUGU_WORDS:
                    tok_lang = "te"
                elif tok_lower in cls.ROMANIZED_KANNADA_WORDS:
                    tok_lang = "kn"
                elif re.match(r'^[a-zA-Z0-9_\.\-]+$', tok_lower):
                    tok_lang = "en"
                else:
                    tok_lang = primary_lang

            if current_lang is None:
                current_lang = tok_lang
                current_segment_text.append(tok)
            elif current_lang == tok_lang:
                current_segment_text.append(tok)
            else:
                # Flush previous segment
                seg_str = "".join(current_segment_text)
                if seg_str.strip():
                    segments.append({"text": seg_str, "language": current_lang})
                current_lang = tok_lang
                current_segment_text = [tok]

        if current_segment_text:
            seg_str = "".join(current_segment_text)
            if seg_str.strip():
                segments.append({"text": seg_str, "language": current_lang or primary_lang})

        return segments

    @classmethod
    def classify_text(
        cls,
        text: str,
        recent_history: Optional[List[Dict[str, Any]]] = None
    ) -> LanguageProfile:
        """
        Classifies input text by script ratios, Unicode ranges, code mixing,
        and Romanized Indic vocabulary. Leverages recent conversational context
        for short/ambiguous messages.
        """
        if not text or not text.strip():
            return LanguageProfile(
                language="en",
                primary_language="en",
                confidence=1.0,
                mode="pure_en",
                language_label="English",
                detection_source="fallback"
            )

        clean = text.strip()
        telugu_matches = re.findall(cls.TELUGU_RANGE, clean)
        kannada_matches = re.findall(cls.KANNADA_RANGE, clean)
        latin_matches = re.findall(cls.LATIN_RANGE, clean)

        telugu_count = len(telugu_matches)
        kannada_count = len(kannada_matches)
        latin_count = len(latin_matches)
        total_letters = telugu_count + kannada_count + latin_count

        words = clean.split()
        is_short_utterance = len(words) <= 5 and total_letters <= 30

        if total_letters == 0:
            return LanguageProfile(
                language="en",
                primary_language="en",
                confidence=1.0,
                mode="pure_en",
                language_label="English",
                detection_source="fallback"
            )

        te_ratio = telugu_count / total_letters
        kn_ratio = kannada_count / total_letters
        en_ratio = latin_count / total_letters

        # Extract isolated English loanwords / technical terms
        english_words = re.findall(r'\b[a-zA-Z0-9_\.\-]{2,}\b', clean)
        words_lower = [w.lower() for w in re.findall(r'[a-zA-Z]+', clean)]
        total_roman_words = max(1, len(words_lower))

        # Check Romanized Telugu & Kannada words
        romanized_te_count = sum(1 for w in words_lower if w in cls.ROMANIZED_TELUGU_WORDS)
        romanized_kn_count = sum(1 for w in words_lower if w in cls.ROMANIZED_KANNADA_WORDS)

        # 1. Telugu Unicode Script classification
        if te_ratio >= 0.12:
            is_mixed = en_ratio >= 0.08 or (len(english_words) >= 1 and te_ratio > 0.3)
            mode = "te+en" if is_mixed else "pure_te"
            label = "తెలుగు + English" if is_mixed else "తెలుగు (Telugu)"
            conf = min(1.0, te_ratio + (en_ratio * 0.5 if is_mixed else 0.0))
            segments = cls.extract_language_segments(clean, primary_lang="te")
            return LanguageProfile(
                language="te",
                primary_language="te",
                secondary_language="en" if is_mixed else None,
                is_code_mixed=is_mixed,
                confidence=round(conf, 3),
                mode=mode,
                indic_script="telugu",
                telugu_ratio=te_ratio,
                kannada_ratio=kn_ratio,
                english_ratio=en_ratio,
                language_label=label,
                english_terms=english_words,
                language_segments=segments,
                detection_source="unicode_script"
            )

        # 2. Kannada Unicode Script classification
        if kn_ratio >= 0.12:
            is_mixed = en_ratio >= 0.08 or (len(english_words) >= 1 and kn_ratio > 0.3)
            mode = "kn+en" if is_mixed else "pure_kn"
            label = "ಕನ್ನಡ + English" if is_mixed else "ಕನ್ನಡ (Kannada)"
            conf = min(1.0, kn_ratio + (en_ratio * 0.5 if is_mixed else 0.0))
            segments = cls.extract_language_segments(clean, primary_lang="kn")
            return LanguageProfile(
                language="kn",
                primary_language="kn",
                secondary_language="en" if is_mixed else None,
                is_code_mixed=is_mixed,
                confidence=round(conf, 3),
                mode=mode,
                indic_script="kannada",
                telugu_ratio=te_ratio,
                kannada_ratio=kn_ratio,
                english_ratio=en_ratio,
                language_label=label,
                english_terms=english_words,
                language_segments=segments,
                detection_source="unicode_script"
            )

        # 3. Romanized Telugu Classification
        if romanized_te_count >= 1 and (
            romanized_te_count / total_roman_words >= 0.15 
            or romanized_te_count >= 2 
            or any(w in {"ela", "unnav", "unnavu", "bagunnanu", "namaskaram", "cheppu", "telugulo", "telugu", "enduku", "vastundi"} for w in words_lower)
        ):
            is_mixed = True
            mode = "te+en"
            label = "తెలుగు + English (Romanized)"
            conf = min(1.0, 0.75 + (romanized_te_count / total_roman_words) * 0.25)
            segments = cls.extract_language_segments(clean, primary_lang="te")
            return LanguageProfile(
                language="te",
                primary_language="te",
                secondary_language="en",
                is_code_mixed=is_mixed,
                confidence=round(conf, 3),
                mode=mode,
                indic_script="telugu",
                telugu_ratio=round(romanized_te_count / total_roman_words, 2),
                kannada_ratio=0.0,
                english_ratio=en_ratio,
                language_label=label,
                english_terms=english_words,
                language_segments=segments,
                detection_source="romanized_lexicon"
            )

        # 4. Romanized Kannada Classification
        if romanized_kn_count >= 1 and (
            romanized_kn_count / total_roman_words >= 0.15 
            or romanized_kn_count >= 2 
            or any(w in {"hege", "iddira", "chennagide", "namaskara", "kannadadalli", "kannada"} for w in words_lower)
        ):
            is_mixed = True
            mode = "kn+en"
            label = "ಕನ್ನಡ + English (Romanized)"
            conf = min(1.0, 0.75 + (romanized_kn_count / total_roman_words) * 0.25)
            segments = cls.extract_language_segments(clean, primary_lang="kn")
            return LanguageProfile(
                language="kn",
                primary_language="kn",
                secondary_language="en",
                is_code_mixed=is_mixed,
                confidence=round(conf, 3),
                mode=mode,
                indic_script="kannada",
                telugu_ratio=0.0,
                kannada_ratio=round(romanized_kn_count / total_roman_words, 2),
                english_ratio=en_ratio,
                language_label=label,
                english_terms=english_words,
                language_segments=segments,
                detection_source="romanized_lexicon"
            )

        # Ambiguous short conversational acknowledgements (e.g. "ok", "sure", "yes", "thanks")
        ambiguous_short_words = {
            "ok", "okay", "sure", "yes", "yeah", "yep", "thanks", "thank you",
            "hmm", "right", "fine", "cool", "done", "got it", "continue", "next", "start"
        }
        clean_lower_words = [w.strip(".,!?:;\"'()").lower() for w in words]
        is_ambiguous_ack = any(w in ambiguous_short_words for w in clean_lower_words) or (len(words) <= 2 and total_letters <= 12)

        # 5. Contextual fallback for short ambiguous queries (e.g. "ok", "yes", "sure", "thanks")
        if is_ambiguous_ack and recent_history:
            last_turn = recent_history[-1]
            last_user_text = str(last_turn.get("user", "") if isinstance(last_turn, dict) else getattr(last_turn, "content", ""))
            if bool(re.search(cls.TELUGU_RANGE, last_user_text)) or any(w in cls.ROMANIZED_TELUGU_WORDS for w in last_user_text.lower().split()):
                segments = cls.extract_language_segments(clean, primary_lang="te")
                return LanguageProfile(
                    language="te",
                    primary_language="te",
                    secondary_language="en",
                    is_code_mixed=True,
                    confidence=0.80,
                    mode="te+en",
                    indic_script="telugu",
                    telugu_ratio=0.5,
                    kannada_ratio=0.0,
                    english_ratio=en_ratio,
                    language_label="తెలుగు + English",
                    english_terms=english_words,
                    language_segments=segments,
                    detection_source="conversation_context"
                )
            elif bool(re.search(cls.KANNADA_RANGE, last_user_text)) or any(w in cls.ROMANIZED_KANNADA_WORDS for w in last_user_text.lower().split()):
                segments = cls.extract_language_segments(clean, primary_lang="kn")
                return LanguageProfile(
                    language="kn",
                    primary_language="kn",
                    secondary_language="en",
                    is_code_mixed=True,
                    confidence=0.80,
                    mode="kn+en",
                    indic_script="kannada",
                    telugu_ratio=0.0,
                    kannada_ratio=0.5,
                    english_ratio=en_ratio,
                    language_label="ಕನ್ನಡ + English",
                    english_terms=english_words,
                    language_segments=segments,
                    detection_source="conversation_context"
                )

        # 6. Default to English
        segments = cls.extract_language_segments(clean, primary_lang="en")
        return LanguageProfile(
            language="en",
            primary_language="en",
            secondary_language=None,
            is_code_mixed=False,
            confidence=round(en_ratio if en_ratio > 0 else 1.0, 3),
            mode="pure_en",
            indic_script=None,
            telugu_ratio=te_ratio,
            kannada_ratio=kn_ratio,
            english_ratio=en_ratio,
            language_label="English",
            english_terms=english_words,
            language_segments=segments,
            detection_source="unicode_script" if en_ratio > 0.5 else "fallback"
        )

    @classmethod
    def detect_explicit_response_language_request(cls, text: str) -> Optional[str]:
        """
        Detects if the user explicitly requested a specific response language
        (e.g., 'explain in english', 'telugulo cheppu', 'kannadadalli heli').
        Returns 'en', 'te', 'kn', or None.
        """
        if not text:
            return None
        text_lower = text.lower().strip()

        if any(re.search(p, text_lower) for p in cls.EXPLICIT_ENGLISH_PATTERNS):
            return "en"
        if any(re.search(p, text_lower) for p in cls.EXPLICIT_TELUGU_PATTERNS):
            return "te"
        if any(re.search(p, text_lower) for p in cls.EXPLICIT_KANNADA_PATTERNS):
            return "kn"
        return None

    @classmethod
    def determine_target_response_language(
        cls,
        input_profile: LanguageProfile,
        user_query: str,
        manual_mode: Optional[str] = "AUTO",
        recent_history: Optional[List[Dict[str, Any]]] = None
    ) -> LanguageProfile:
        """
        Determines the authoritative target response language profile:
        1. Explicit user in-query request (e.g. 'Explain this in English') takes top priority.
        2. Manual language override (e.g., 'te', 'kn', 'en') takes second priority if not 'AUTO'.
        3. Detected input language profile is used as default.
        """
        explicit_req = cls.detect_explicit_response_language_request(user_query)
        norm_manual = (manual_mode or "AUTO").upper().strip()

        # 1. Explicit request in the message
        if explicit_req:
            if explicit_req == "en":
                return LanguageProfile(
                    language="en",
                    primary_language="en",
                    secondary_language=None,
                    is_code_mixed=False,
                    mode="pure_en",
                    language_label="English",
                    confidence=0.98,
                    detection_source="explicit_request",
                    requested_output_language="en",
                    manual_mode=manual_mode,
                    language_segments=input_profile.language_segments
                )
            elif explicit_req == "te":
                return LanguageProfile(
                    language="te",
                    primary_language="te",
                    secondary_language="en" if input_profile.is_code_mixed else None,
                    is_code_mixed=input_profile.is_code_mixed,
                    mode="te+en" if input_profile.is_code_mixed else "pure_te",
                    indic_script="telugu",
                    language_label="తెలుగు (Telugu)",
                    confidence=0.98,
                    detection_source="explicit_request",
                    requested_output_language="te",
                    manual_mode=manual_mode,
                    language_segments=input_profile.language_segments
                )
            elif explicit_req == "kn":
                return LanguageProfile(
                    language="kn",
                    primary_language="kn",
                    secondary_language="en" if input_profile.is_code_mixed else None,
                    is_code_mixed=input_profile.is_code_mixed,
                    mode="kn+en" if input_profile.is_code_mixed else "pure_kn",
                    indic_script="kannada",
                    language_label="ಕನ್ನಡ (Kannada)",
                    confidence=0.98,
                    detection_source="explicit_request",
                    requested_output_language="kn",
                    manual_mode=manual_mode,
                    language_segments=input_profile.language_segments
                )

        # 2. Manual Mode Override
        if norm_manual in ["EN", "ENGLISH"]:
            return LanguageProfile(
                language="en",
                primary_language="en",
                secondary_language=input_profile.secondary_language,
                is_code_mixed=input_profile.is_code_mixed,
                mode="pure_en",
                language_label="English (Manual)",
                confidence=1.0,
                detection_source="manual_override",
                manual_mode="EN",
                language_segments=input_profile.language_segments
            )
        elif norm_manual in ["TE", "TELUGU", "తెలుగు"]:
            return LanguageProfile(
                language="te",
                primary_language="te",
                secondary_language="en" if input_profile.is_code_mixed else None,
                is_code_mixed=input_profile.is_code_mixed,
                mode="te+en" if input_profile.is_code_mixed else "pure_te",
                indic_script="telugu",
                language_label="తెలుగు (Manual)",
                confidence=1.0,
                detection_source="manual_override",
                manual_mode="TE",
                language_segments=input_profile.language_segments
            )
        elif norm_manual in ["KN", "KANNADA", "ಕನ್ನಡ"]:
            return LanguageProfile(
                language="kn",
                primary_language="kn",
                secondary_language="en" if input_profile.is_code_mixed else None,
                is_code_mixed=input_profile.is_code_mixed,
                mode="kn+en" if input_profile.is_code_mixed else "pure_kn",
                indic_script="kannada",
                language_label="ಕನ್ನಡ (Manual)",
                confidence=1.0,
                detection_source="manual_override",
                manual_mode="KN",
                language_segments=input_profile.language_segments
            )

        # 3. Default to input language profile
        input_profile.manual_mode = "AUTO"
        return input_profile

    @classmethod
    def normalize_for_speech(cls, text: str, language: str = "en") -> str:
        """
        Prepares multilingual text for natural acoustic TTS synthesis:
        - Preserves English technical terms, code variables, framework names verbatim.
        - Normalizes punctuation, markdown, and emojis.
        """
        if not text:
            return ""

        s = text
        # 1. Remove code blocks
        s = re.sub(r'```[\s\S]*?```', '', s)
        # 2. Extract inline backticks cleanly
        s = re.sub(r'`([^`]+)`', r'\1', s)
        # 3. Clean markdown headers and formatting
        s = re.sub(r'#+\s*', '', s)
        s = re.sub(r'[*_]{1,3}([^*_]+)[*_]{1,3}', r'\1', s)
        s = re.sub(r'!\[.*?\]\(.*?\)', '', s)
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        s = re.sub(r'^\s*[-*+]\s+', '', s, flags=re.MULTILINE)
        # 4. Remove emojis and unusual symbols
        s = re.sub(r'[\U00010000-\U0010ffff]', '', s)
        s = re.sub(r'[\u2600-\u26ff\u2700-\u27bf]', '', s)
        # 5. Clean whitespace
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    @classmethod
    def expand_memory_query_terms(cls, query: str) -> Set[str]:
        """
        Expands user query terms into cross-lingual semantic equivalents.
        Allows a Telugu or Kannada query to retrieve memories saved in English,
        and an English query to retrieve memories saved in Telugu or Kannada.
        """
        query_words = {w for w in re.findall(r'[^\s\.,!?:;\"\'()\[\]{}<>/\\#*`~_]+', query.lower()) if len(w) > 1}
        expanded_terms = set(query_words)

        for concept, synonyms in cls.CROSS_LINGUAL_SYNONYMS.items():
            if any(syn.lower() in query.lower() or syn.lower() in query_words for syn in synonyms):
                expanded_terms.update(synonyms)
                expanded_terms.add(concept)

        return expanded_terms

    @classmethod
    def get_language_directive(cls, lang_profile: LanguageProfile) -> str:
        """
        Generates the system prompt directive ensuring Saki responds naturally in the
        appropriate language while preserving English code and technical loanwords.
        """
        if lang_profile.language == "te":
            return (
                "\nMULTILINGUAL DIRECTIVE (Telugu / తెలుగు):\n"
                "- Converse naturally, fluently, and warmly in authentic conversational Telugu (తెలుగు).\n"
                "- Do NOT use overly formal, archaic, or textbook language. Speak like a close, smart friend.\n"
                "- Keep programming code, technical terms, framework names (e.g. Python, FastAPI, React, Next.js), numbers, and natural English loanwords in English.\n"
                "- Preserve Saki's unified companionable, empathetic, and intelligent identity across languages."
            )
        elif lang_profile.language == "kn":
            return (
                "\nMULTILINGUAL DIRECTIVE (Kannada / ಕನ್ನಡ):\n"
                "- Converse naturally, fluently, and warmly in authentic conversational Kannada (ಕನ್ನಡ).\n"
                "- Do NOT use overly formal, archaic, or textbook language. Speak like a close, smart friend.\n"
                "- Keep programming code, technical terms, framework names (e.g. Python, FastAPI, React, Next.js), numbers, and natural English loanwords in English.\n"
                "- Preserve Saki's unified companionable, empathetic, and intelligent identity across languages."
            )
        return ""


# Singleton instance
multilingual_service = MultilingualService()
