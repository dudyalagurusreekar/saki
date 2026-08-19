"""
Test different Gemini model endpoints for quota and Google Search grounding support.
"""
import httpx
import time
from backend.core.config import settings

MODELS_TO_TEST = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.5-flash"
]

def test_models():
    api_key = settings.GEMINI_API_KEY
    for model_name in MODELS_TO_TEST:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "What is the current version of FastAPI?"}]
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
                print(f"   Success! Grounding queries: {queries}")
                print(f"   Grounding chunks: {len(chunks)}")
                print(f"   Response text: {text[:150]}...")
            else:
                print(f"   Error: {resp.text[:200]}")
        except Exception as e:
            print(f"Model: {model_name} -> Exception: {e}")
        time.sleep(1)

if __name__ == "__main__":
    test_models()
