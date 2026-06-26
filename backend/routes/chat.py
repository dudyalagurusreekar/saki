from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.models.schemas import ChatRequest
from backend.services.ai_service import call_model, call_model_with, stream_model, detect_intent
from backend.services.memory_service import build_memory_context, load_memory, update_memory
from backend.services.search_service import safe_search
from backend.services.news_service import get_safe_news
from backend.core.config import settings

router = APIRouter()


def build_saki_prompt(user_input: str, memory_context: str) -> str:
    return f"""
You are Saki, a warm local-first AI companion.

Use durable memory only when it is relevant. Do not mention memory mechanics.

Durable memory:
{memory_context}

Rules:
- Be natural
- Keep it short
- Do not say "As an AI"
- If memory is uncertain, ask gently instead of assuming

User: {user_input}

Answer:
"""



@router.post("/chat/stream")
def chat_stream(req: ChatRequest):

    user_input = req.message.strip()

    memory = load_memory()
    memory_context = build_memory_context(memory, user_input, settings.MEMORY_CONTEXT_LIMIT)
    intent = detect_intent(user_input)

    # -------------------------
    # BUILD PROMPT (same logic)
    # -------------------------
    if intent == "emotional":
        prompt = f"""
You are Saki, a caring, supportive local-first AI companion.

Durable memory:
{memory_context}

User: {user_input}

Respond with empathy and warmth.
"""
        model = settings.MODEL_EMO

    elif intent == "news":
        news_data = get_safe_news()

        prompt = f"""
Summarize these headlines clearly:

{news_data}

User context, if useful:
{memory_context}
"""
        model = settings.MODEL_FAST

    else:
        prompt = build_saki_prompt(user_input, memory_context)
        model = settings.MODEL_FAST

    # -------------------------
    # STREAM GENERATOR
    # -------------------------
    def generate():

        full_response = ""

        for chunk in stream_model(prompt, model=model):
            full_response += chunk
            yield chunk

        # fallback search AFTER streaming if needed
        if (
            len(full_response.strip()) < 20 or
            any(x in full_response.lower() for x in [
                "i don't know", "not sure", "cannot answer"
            ])
        ):
            results = safe_search(user_input)

            if results:
                follow_prompt = f"""
Answer using these results:

{results}
"""
                for chunk in stream_model(follow_prompt, model=settings.MODEL_FAST):
                    full_response += chunk
                    yield chunk

        # update memory AFTER full response
        update_memory(memory, user_input, full_response.strip())

    return StreamingResponse(generate(), media_type="text/plain")

def clean_response(text: str) -> str:
    lines = text.split("\n")
    clean = []

    for l in lines:
        l = l.strip()
        if l and l not in clean:
            clean.append(l)

    return " ".join(clean[:3])


@router.post("/chat")
def chat(req: ChatRequest):
    user_input = req.message.strip()

    memory = load_memory()
    memory_context = build_memory_context(memory, user_input, settings.MEMORY_CONTEXT_LIMIT)
    intent = detect_intent(user_input)

    # -------------------------
    # EMOTIONAL RESPONSE
    # -------------------------
    if intent == "emotional":
        prompt = f"""
You are Saki, a caring, supportive local-first AI companion.

Durable memory:
{memory_context}

User: {user_input}

Respond with empathy and warmth.
"""
        response = call_model_with(settings.MODEL_EMO, prompt)

    # -------------------------
    # NEWS
    # -------------------------
    elif intent == "news":
        news_data = get_safe_news()

        prompt = f"""
Summarize these headlines clearly:

{news_data}

User context, if useful:
{memory_context}
"""
        response = call_model(prompt)

    # -------------------------
    # NORMAL CHAT / QUESTION
    # -------------------------
    else:
        prompt = build_saki_prompt(user_input, memory_context)
        response = call_model(prompt)

        # -------------------------
        # FALLBACK SEARCH
        # -------------------------
        if not response or len(response) < 20 or any(x in response.lower() for x in [
            "i don't know", "not sure", "cannot answer"
        ]):
            results = safe_search(user_input)

            if results:
                response = call_model(f"""
Answer using these results:

{results}
""")

    response = clean_response(response)

    update_memory(memory, user_input, response)

    return {
        "response": response
    }
