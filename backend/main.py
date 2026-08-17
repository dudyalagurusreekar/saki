from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.chat import router as chat_router
from backend.routes.memory import router as memory_router
from backend.routes.system import router as system_router
from backend.routes.world_access import router as world_access_router

app = FastAPI(
    title="Saki AI Backend",
    version="1.0",
    description="Private AI assistant backend with native privacy-controlled world access",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(world_access_router, prefix="/api")


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Saki AI",
        "version": "1.0",
        "world_access": "native",
    }
