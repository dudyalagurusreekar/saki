"""
Test search grounding across all supported flash models.
"""
import httpx
from backend.core.config import settings

api_key = settings.GEMINI_API_KEY
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash"
]

for m in MODELS:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "What is the current version of FastAPI?"}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256}
    }
    with httpx.Client(timeout=10.0) as client:
        r = client.post(url, json=payload)
    print(f"Model: {m} -> Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        print(f"   Success: {text[:150]}...")
    elif r.status_code == 429:
        msg = r.json().get("error", {}).get("message", "")
        print(f"   429: {msg[:100]}")
    else:
        print(f"   Error: {r.text[:100]}")
