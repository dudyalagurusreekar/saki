"""
Test daily quotas for different models.
"""
import httpx
from backend.core.config import settings

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

api_key = settings.GEMINI_API_KEY
for m in MODELS:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Say ok"}]}],
        "generationConfig": {"maxOutputTokens": 5}
    }
    with httpx.Client() as client:
        r = client.post(url, json=payload)
    print(f"Model: {m} -> Status: {r.status_code}")
    if r.status_code == 200:
        print(f"   Success text: {r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')}")
    else:
        err = r.json().get("error", {}).get("message", "")
        print(f"   Error: {err[:150]}")
