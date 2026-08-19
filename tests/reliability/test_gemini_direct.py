"""
Direct Gemini Search API Call Inspector
"""
import httpx
from backend.core.config import settings

def test_gemini_direct(query: str = "what current fastapi version"):
    api_key = settings.GEMINI_API_KEY
    model_name = getattr(settings, "GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    print(f"Model: {model_name}")
    print(f"API Key present: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
    
    task_prompt = (
        f"TASK:\n"
        f"Retrieve and extract the factual information required to answer the user's question.\n\n"
        f"USER QUESTION:\n"
        f"{query}\n\n"
        f"REQUIRED INFORMATION:\n"
        f"- Exact entity identification and details\n"
        f"- Core facts, dates, or figures requested\n"
        f"- Supporting source facts\n\n"
        f"RETURN:\n"
        f"A clean, factual summary containing the requested information and source URLs."
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": task_prompt}]
            }
        ],
        "tools": [
            {"google_search": {}}
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024
        }
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload)
        print(f"Status Code: {resp.status_code}")
        print(f"Response Body:\n{resp.text[:1000]}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_gemini_direct()
