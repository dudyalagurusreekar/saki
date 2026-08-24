import os
from dotenv import load_dotenv

# Load local environment variables from .env file at startup
load_dotenv()

class Settings:
    """
    Central configuration for the entire backend system.
    Modify values here instead of hardcoding elsewhere.
    """

    # -------------------------
    # APP INFO
    # -------------------------
    APP_NAME = "Saki AI"
    VERSION = "1.0"

    # Project workspace root (auto-detected from config location)
    WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))  

    # Frontend origin for CORS
    FRONTEND_ORIGIN = "http://localhost:3000"

    # -------------------------
    # PRIVACY CONTROL
    # -------------------------
    # HIGH → fully private (no external calls)
    # MEDIUM → safe external usage (recommended)
    # LOW → unrestricted
    PRIVACY_MODE = "MEDIUM"

    # -------------------------
    # MODELS (Saki Local Model Orchestrator)
    # -------------------------
    MODEL_PHI3 = "phi3:latest"
    MODEL_HERMES = "nous-hermes2:latest"
    MODEL_QWEN3 = "qwen3:8b"
    MODEL_QWEN = "qwen3:8b"
    MODEL_CODER = "qwen2.5-coder:7b"
    MODEL_GEMMA = "gemma3:4b"

    # Backward compatibility fallbacks
    MODEL_FAST = "phi3:latest"
    MODEL_EMO = "nous-hermes2:latest"
    MODEL_DEFAULT = "qwen3:8b"

    # Model Idle Timeout in seconds (for unloading)
    MODEL_KEEP_ALIVE_SESSION = "5m"
    MODEL_KEEP_ALIVE_UNLOAD = "0s"

    # -------------------------
    # STABLE CORE TRANSLATION FLOW
    # Detect language -> translate input to English -> route & generate in English
    # -> translate response back to user's language -> speak via TTS
    # -------------------------
    ENABLE_TRANSLATION = True
    # Fast multilingual local model used for both translation directions
    TRANSLATION_MODEL = os.environ.get("TRANSLATION_MODEL", "gemma3:4b")

    # -------------------------
    # MEMORY CONTROL
    # -------------------------
    MAX_MEMORY = 10
    MAX_DURABLE_MEMORIES = 300
    MEMORY_CONTEXT_LIMIT = 6

    # -------------------------
    # AUDIO, VAD & TTS
    # -------------------------
    VAD_SILENCE_TIMEOUT_MS = 2000
    VAD_SPEECH_THRESHOLD = 0.015
    SAKI_TTS_VOICE_EN = "af_heart"
    SAKI_TTS_VOICE_TE = "te_saki"
    SAKI_TTS_VOICE_KN = "kn_saki"
    SAKI_TTS_SPEED_EN = 1.0
    SAKI_TTS_SPEED_TE = 1.0
    SAKI_TTS_SPEED_KN = 1.0

    # -------------------------
    # API KEYS & EXTERNAL PROVIDERS
    # -------------------------
    NEWS_API_KEY = "your_news_api_key_here"
    
    # Controlled External Intelligence & Web Provider (Google Search Grounding)
    GEMINI_API_KEY = os.environ.get(
        "GEMINI_API_KEY", 
        "your_gemini_api_key_here"
    )
    GEMINI_SEARCH_MODEL = os.environ.get("GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
    SEARCH_PROVIDER = os.environ.get("SEARCH_PROVIDER", "gemini")  # "gemini", "duckduckgo", "hybrid"
    ENABLE_GEMINI_SEARCH = True

    # -------------------------
    # EMOTIONAL SUPPORT & HERMES ACTIVATION THRESHOLDS
    # -------------------------
    HERMES_SUPPORT_HIGH_THRESHOLD: float = 0.70
    HERMES_SUPPORT_MODERATE_THRESHOLD: float = 0.50
    HERMES_SUPPORT_LOW_THRESHOLD: float = 0.30
    HERMES_UNCERTAINTY_FALLBACK_MODEL: str = "qwen3:8b"

    # -------------------------
    # LOCAL MULTILINGUAL TTS VOICE CONFIGURATION (Sprint 7)
    # -------------------------
    SAKI_TTS_VOICE_EN: str = os.environ.get("SAKI_TTS_VOICE_EN", "af_heart")
    SAKI_TTS_VOICE_TE: str = os.environ.get("SAKI_TTS_VOICE_TE", "te_saki")
    SAKI_TTS_VOICE_KN: str = os.environ.get("SAKI_TTS_VOICE_KN", "kn_saki")
    SAKI_TTS_SPEED_EN: float = float(os.environ.get("SAKI_TTS_SPEED_EN", "1.0"))
    SAKI_TTS_SPEED_TE: float = float(os.environ.get("SAKI_TTS_SPEED_TE", "1.0"))
    SAKI_TTS_SPEED_KN: float = float(os.environ.get("SAKI_TTS_SPEED_KN", "1.0"))


# Global settings instance
settings = Settings()

