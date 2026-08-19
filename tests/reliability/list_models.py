"""
List all available Gemini models for the configured API key.
"""
import httpx
from backend.core.config import settings

def list_gemini_models():
    api_key = settings.GEMINI_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        print(f"Found {len(models)} models:")
        for m in models:
            name = m.get("name")
            supported = m.get("supportedGenerationMethods", [])
            print(f" - {name} ({', '.join(supported)})")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    list_gemini_models()
