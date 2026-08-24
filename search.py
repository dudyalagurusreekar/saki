import os
import google.generativeai as genai

# -------------------------
# CONFIG
# -------------------------
API_KEY = os.getenv("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

# -------------------------
# GEMINI SEARCH FUNCTION
# -------------------------
def multi_search(query):
    try:
        prompt = f"""
User asked: {query}

Do the following:
1. Understand the question
2. Provide the most accurate and updated answer possible
3. Keep it clear and short
4. Sound natural (not robotic)

Answer:
"""

        response = model.generate_content(prompt)

        text = response.text.strip()

        return [text]

    except Exception as e:
        return [f"Search failed: {e}"]