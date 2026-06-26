from fastapi import APIRouter
from backend.models.schemas import MemoryResponse
from backend.services.memory_service import load_memory

router = APIRouter()


@router.get("/memory", response_model=MemoryResponse)
def get_memory():
    return load_memory()
