from fastapi import APIRouter
from backend.core.config import settings

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok"
    }


@router.get("/config")
def get_config():
    return {
        "privacy_mode": settings.PRIVACY_MODE,
        "model_fast": settings.MODEL_FAST,
        "model_emo": settings.MODEL_EMO,
        "max_memory": settings.MAX_MEMORY
    }