"""
Test available flash models for Google Search Grounding support.
"""
import httpx
import time
from backend.core.config import settings

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite"
]

def test_grounding():
    api_key = settings.GEMINI_API_KEY
    for model_name in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "What is the current version of FastAPI released in 2026?"}]
                }
            ],
            "tools": [
                {"google_search": {}}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 256
            }
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
            print(f"Model: {model_name} -> Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [{}])[0]
                text = cand.get("content", {}).get("parts", [{}])[0].get("text", "")
                grounding = cand.get("groundingMetadata", {})
                chunks = grounding.get("groundingChunks", [])
                queries = grounding.get("webSearchQueries", [])
                print(f"   SUCCESS! queries: {queries}, chunks count: {len(chunks)}")
                print(f"   Grounded Text: {text[:150]}...")
            else:
                print(f"   Error: {resp.text[:200]}")
        except Exception as e:
            print(f"Model: {model_name} -> Exception: {e}")
        time.sleep(1)

if __name__ == "__main__":
    test_grounding()
