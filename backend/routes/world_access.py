from typing import Any, Dict

from fastapi import APIRouter

from backend.core.config import settings
from backend.models.world_access import WorldAccessRequest, WorldAccessAction
from backend.services.world_access import world_access

router = APIRouter()


@router.get("/world-access/status")
def world_access_status() -> Dict[str, Any]:
    return {
        "enabled": bool(settings.WORLD_ACCESS_ENABLED),
        "privacy_mode": settings.PRIVACY_MODE,
        "provider": "searxng",
        "endpoint": settings.SEARXNG_URL,
        "capabilities": ["search", "fetch"],
    }


@router.post("/world-access/search")
def world_access_search(request: WorldAccessRequest):
    request.action = WorldAccessAction.SEARCH
    if not settings.WORLD_ACCESS_ENABLED:
        return {"allowed": False, "error": "World access is disabled"}
    return world_access.search(request).model_dump()
