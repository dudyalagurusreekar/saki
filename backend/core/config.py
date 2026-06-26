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

    # -------------------------
    # PRIVACY CONTROL
    # -------------------------
    # HIGH → fully private (no external calls)
    # MEDIUM → safe external usage (recommended)
    # LOW → unrestricted
    PRIVACY_MODE = "MEDIUM"

    # -------------------------
    # MODELS
    # -------------------------
    MODEL_FAST = "phi3"
    MODEL_EMO = "nous-hermes2"

    # -------------------------
    # MEMORY CONTROL
    # -------------------------
    MAX_MEMORY = 10
    MAX_DURABLE_MEMORIES = 300
    MEMORY_CONTEXT_LIMIT = 6

    # -------------------------
    # API KEYS
    # -------------------------
    NEWS_API_KEY = "your_news_api_key_here"


# Global settings instance
settings = Settings()
