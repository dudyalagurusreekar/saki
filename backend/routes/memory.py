from fastapi import APIRouter
from backend.services.memory_service import load_memory

router = APIRouter()


@router.get("/memory")
def get_memory():
    return load_memory()