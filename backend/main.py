from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -------------------------
# ROUTES
# -------------------------
from backend.routes.chat import router as chat_router
from backend.routes.memory import router as memory_router
from backend.routes.system import router as system_router
from backend.routes.voice import router as voice_router
from backend.routes.microphone import router as microphone_router

# -------------------------
# APP INIT
# -------------------------
app = FastAPI(
    title="Saki AI Backend",
    version="1.0",
    description="Private AI assistant backend with FastAPI"
)

# -------------------------
# CORS (IMPORTANT for frontend)
# -------------------------
from backend.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# ROUTE REGISTRATION
# -------------------------
app.include_router(chat_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(microphone_router)

# -------------------------
# ROOT ENDPOINT
# -------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Saki AI",
        "version": "1.0"
    }