import httpx
import json
from backend.core.config import settings


# -------------------------
# MAIN MODEL CALL
# -------------------------
def call_model(prompt: str, model: str = None) -> str:
    model = model or settings.MODEL_FAST

    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60.0
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return f"Error: Ollama returned status code {response.status_code}"
    except Exception as e:
        return f"Error calling Ollama API: {str(e)}"


# -------------------------
# CUSTOM MODEL CALL
# -------------------------
def call_model_with(model: str, prompt: str) -> str:
    return call_model(prompt, model)


# -------------------------
# STREAMING
# -------------------------
def stream_model(prompt: str, model: str = None):
    model = model or settings.MODEL_FAST
    try:
        with httpx.stream(
            "POST",
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True
            },
            timeout=60.0
        ) as r:
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
    except Exception as e:
        yield f"Error in stream: {str(e)}"


def detect_intent(user_input: str) -> str:
    text = user_input.lower()

    if any(w in text for w in [
        "sad", "lonely", "depressed", "anxious",
        "tired", "stress", "upset"
    ]):
        return "emotional"

    if any(w in text for w in [
        "news", "latest", "headline", "today"
    ]):
        return "news"

    if any(w in text for w in [
        "hi", "hello", "hey"
    ]):
        return "chat"

    return "question"