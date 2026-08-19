"""
Test Google Search tool on available models.
"""
import httpx
from backend.core.config import settings

api_key = settings.GEMINI_API_KEY
MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

for m in MODELS:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "What is the current version of FastAPI in 2026?"}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": 256}
    }
    with httpx.Client(timeout=15.0) as client:
        r = client.post(url, json=payload)
    print(f"Model: {m} -> Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        cand = data.get("candidates", [{}])[0]
        text = cand.get("content", {}).get("parts", [{}])[0].get("text", "")
        grounding = cand.get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])
        queries = grounding.get("webSearchQueries", [])
        print(f"   Success! Grounding queries: {queries}")
        print(f"   Grounding chunks: {len(chunks)}")
        print(f"   Grounding text: {text[:200]}...")
    else:
        print(f"   Error: {r.text[:200]}")
