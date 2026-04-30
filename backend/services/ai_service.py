import subprocess
from backend.core.config import settings


# -------------------------
# MAIN MODEL CALL
# -------------------------
def call_model(prompt: str, model: str = None) -> str:
    model = model or settings.MODEL_FAST

    try:
        result = subprocess.run(
            ["ollama", "generate", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60
        )

        output = result.stdout.strip()

        if not output:
            return "Hmm... I didn't get that."

        return output

    except Exception as e:
        return f"Error: {str(e)}"


# -------------------------
# CUSTOM MODEL CALL
# -------------------------
def call_model_with(model: str, prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "generate", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60
        )
        return result.stdout.strip()

    except Exception as e:
        return f"Error: {str(e)}"


# -------------------------
# STREAMING (TEMP SIMPLE)
# -------------------------
def stream_model(prompt: str, model: str = None):
    model = model or settings.MODEL_FAST
    response = call_model(prompt, model)
    for word in response.split():
        yield word + " "


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