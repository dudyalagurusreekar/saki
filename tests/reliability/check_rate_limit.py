"""
Inspect full 429 rate limit details.
"""
import httpx
from backend.core.config import settings

api_key = settings.GEMINI_API_KEY
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
payload = {
    "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
    "generationConfig": {"maxOutputTokens": 10}
}
with httpx.Client() as client:
    r = client.post(url, json=payload)
print(f"Status: {r.status_code}")
print(r.text)
