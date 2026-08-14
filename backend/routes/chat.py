from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from backend.models.schemas import ChatRequest
from backend.services.ai_service import call_model, call_model_with, stream_model, detect_intent
from backend.services.memory_service import build_memory_context, load_memory, update_memory
from backend.services.search_service import safe_search
from backend.services.news_service import get_safe_news
from backend.core.config import settings

router = APIRouter()


def get_attachment_context(req: ChatRequest) -> str:
    """Helper to analyze uploaded attachments and construct a descriptive text block for the LLM."""
    if not req.attachments:
        return ""
    
    from brain.attachment_analyzer import analyze_attachment
    analyzed_list = []
    for att in req.attachments:
        try:
            analyzed = analyze_attachment(att)
            analyzed_list.append(analyzed)
        except Exception as e:
            print(f"Error analyzing attachment: {e}")
            
    if not analyzed_list:
        return ""
        
    context = "\n\n[Uploaded Files Information]:\n"
    for att in analyzed_list:
        context += f"- Name: {att.name}\n  Type: {att.type}\n  Size: {att.size}\n  Pages/Rows/Files: {att.pages or 1}\n"
        if att.metadata and "error" not in att.metadata:
            context += f"  Metadata: {att.metadata}\n"
    return context


def format_history_context(history: list) -> str:
    """Compile recent conversation turns into context for the prompt."""
    if not history:
        return ""
    formatted = "\nRecent Conversation History:\n"
    for turn in history[-6:]:  # last 6 turns (user + saki pairs)
        formatted += f"- User: {turn.get('user')}\n- Saki: {turn.get('saki')}\n"
    return formatted


def is_helpless_response(text: str) -> bool:
    """Check if the model response is empty, too short, or indicates it cannot answer."""
    if not text or len(text.strip()) < 15:
        return True
    text_lower = text.lower()
    helpless_phrases = [
        "i don't know", "i do not know", "not sure", "cannot answer", 
        "unable to answer", "no information available", "apologize, but i cannot",
        "don't have access", "i'm not sure", "cannot find", "sorry, but i don't",
        "apologize, i cannot"
    ]
    return any(phrase in text_lower for phrase in helpless_phrases)


def clean_speaker_prefix(text: str) -> str:
    """Strip redundant speaker names or colons from the beginning of the text."""
    if not text:
        return ""
    text_strip = text.strip()
    text_lower = text_strip.lower()
    
    # Check for "saki:" prefix
    if text_lower.startswith("saki:"):
        return text_strip[5:].strip()
    # Check for "saki -" prefix
    if text_lower.startswith("saki -"):
        return text_strip[6:].strip()
    # Check for "saki " prefix
    if text_lower.startswith("saki "):
        return text_strip[5:].strip()
    # Check if it is exactly "saki"
    if text_lower == "saki":
        return ""
        
    return text_strip


def build_saki_prompt(user_input: str, memory_context: str, history_context: str) -> str:
    return f"""
You are Saki, a warm local-first AI companion.

Use durable memory only when it is relevant. Do not mention memory mechanics.

Durable memory:
{memory_context}
{history_context}

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
    # Inject attachments details if present
    attachment_context = get_attachment_context(req)
    prompt_input = user_input + attachment_context

    memory = load_memory()
    memory_context = build_memory_context(memory, user_input, settings.MEMORY_CONTEXT_LIMIT)
    history_context = format_history_context(memory.get("conversation_history", []))
    intent = detect_intent(user_input)

    # -------------------------
    # BUILD PROMPT
    # -------------------------
    if intent == "emotional":
        prompt = f"""
You are Saki, a caring, supportive local-first AI companion.

Durable memory:
{memory_context}
{history_context}

User: {prompt_input}

Respond with empathy and warmth, and support the user based on the conversation history.
"""
        model = settings.MODEL_EMO

    elif intent == "news":
        news_data = get_safe_news()

        prompt = f"""
Summarize these headlines clearly:

{news_data}

User: {prompt_input}

User context, if useful:
{memory_context}
{history_context}
"""
        model = settings.MODEL_FAST

    else:
        prompt = build_saki_prompt(prompt_input, memory_context, history_context)
        model = settings.MODEL_FAST

    # -------------------------
    # STREAM GENERATOR
    # -------------------------
    def generate():
        full_response = ""
        buffered_text = ""
        stripped_prefix = False

        for chunk in stream_model(prompt, model=model):
            full_response += chunk
            
            if not stripped_prefix:
                buffered_text += chunk
                buff_lower = buffered_text.lower().strip()
                
                if buff_lower.startswith("saki"):
                    if ":" in buffered_text:
                        parts = buffered_text.split(":", 1)
                        buffered_text = parts[1].lstrip()
                        stripped_prefix = True
                        if buffered_text:
                            yield buffered_text
                            buffered_text = ""
                    elif len(buffered_text) > 12:
                        if buff_lower.startswith("saki "):
                            buffered_text = buffered_text[5:].lstrip()
                        stripped_prefix = True
                        yield buffered_text
                        buffered_text = ""
                else:
                    stripped_prefix = True
                    yield buffered_text
                    buffered_text = ""
            else:
                yield chunk

        # Flush buffer if we finished early and didn't strip
        if not stripped_prefix and buffered_text:
            clean_buf = buffered_text.strip()
            if clean_buf.lower() != "saki" and not clean_buf.lower().startswith("saki:"):
                yield buffered_text

        # fallback search AFTER streaming if needed
        if is_helpless_response(full_response):
            results = safe_search(user_input)

            if results:
                follow_prompt = f"""
Answer using these results:

{results}
"""
                # Stream fallback search response
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
    attachment_context = get_attachment_context(req)
    prompt_input = user_input + attachment_context

    memory = load_memory()
    memory_context = build_memory_context(memory, user_input, settings.MEMORY_CONTEXT_LIMIT)
    history_context = format_history_context(memory.get("conversation_history", []))
    intent = detect_intent(user_input)

    # -------------------------
    # EMOTIONAL RESPONSE
    # -------------------------
    if intent == "emotional":
        prompt = f"""
You are Saki, a caring, supportive local-first AI companion.

Durable memory:
{memory_context}
{history_context}

User: {prompt_input}

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

User: {prompt_input}

User context, if useful:
{memory_context}
{history_context}
"""
        response = call_model(prompt)

    # -------------------------
    # NORMAL CHAT / QUESTION
    # -------------------------
    else:
        prompt = build_saki_prompt(prompt_input, memory_context, history_context)
        response = call_model(prompt)

        # -------------------------
        # FALLBACK SEARCH
        # -------------------------
        if is_helpless_response(response):
            results = safe_search(user_input)

            if results:
                response = call_model(f"""
Answer using these results:

{results}
""")

    response = clean_response(response)
    response = clean_speaker_prefix(response)

    update_memory(memory, user_input, response)

    return {
        "response": response
    }


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    import os
    # Save the file to data/uploads/
    upload_dir = os.path.abspath(os.path.join(os.getcwd(), "data", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    # Write the bytes
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    return {
        "name": file.filename,
        "path": file_path,
        "size": len(content)
    }
