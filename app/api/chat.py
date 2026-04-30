from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.schema import ChatRequest
from app.services.llm import stream_llm

router = APIRouter()

@router.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        async for chunk in stream_llm(req.messages):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
