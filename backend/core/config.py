class Settings:
    """Central configuration for Saki's local cognition and external world access."""

    APP_NAME = "Saki AI"
    VERSION = "1.0"

    # PRIVACY CONTROL
    # HIGH -> no external world access
    # MEDIUM -> external access only through the privacy-controlled World Access layer
    # LOW -> World Access still enforces secret blocking, but allows contextual queries
    PRIVACY_MODE = "MEDIUM"

    # WORLD ACCESS
    WORLD_ACCESS_ENABLED = True
    SEARXNG_URL = "http://127.0.0.1:8080"
    WORLD_ACCESS_TIMEOUT = 10.0
    WORLD_ACCESS_USER_AGENT = "SakiWorldAccess/1.0"

    # MODELS
    MODEL_PHI3 = "phi3:latest"
    MODEL_HERMES = "nous-hermes2:latest"
    MODEL_QWEN3 = "qwen3:8b"
    MODEL_CODER = "qwen2.5-coder:7b"
    MODEL_GEMMA = "gemma3:4b"
    MODEL_FAST = "phi3:latest"
    MODEL_EMO = "nous-hermes2:latest"
    MODEL_DEFAULT = "qwen3:8b"

    MODEL_KEEP_ALIVE_SESSION = "5m"
    MODEL_KEEP_ALIVE_UNLOAD = "0s"

    # MEMORY CONTROL
    MAX_MEMORY = 10
    MAX_DURABLE_MEMORIES = 300
    MEMORY_CONTEXT_LIMIT = 6

    # API KEYS
    NEWS_API_KEY = "your_news_api_key_here"


settings = Settings()
