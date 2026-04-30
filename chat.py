import subprocess
import json
import time
from search import multi_search
import os
import speech_recognition as sr
from news import get_news

# -------------------------
# PRIVACY MODE
# -------------------------
PRIVACY_MODE = "MEDIUM"
# HIGH → fully private
# MEDIUM → safe Gemini + news
# LOW → full access

MODEL_FAST = "phi3"

# -------------------------
# PIPER CONFIG
# -------------------------
PIPER_PATH = r"D:\applications\piper\piper.exe"
VOICE_PATH = r"D:\applications\piper\en_US-amy-medium.onnx"
TEMP_AUDIO = r"D:\applications\piper\temp.wav"

IDLE_TIMEOUT = 30


MODEL_EMO = "nous-hermes2"
MAX_MEMORY = 10

# -------------------------
# INTENT DETECTION
# -------------------------
def detect_intent(user_input):
    text = user_input.lower()

    if any(w in text for w in [
        "sad", "lonely", "tired", "depressed", "stress",
        "anxious", "upset", "not feeling good"
    ]):
        return "emotional"

    if any(w in text for w in [
        "news", "today", "latest", "headline", "current"
    ]):
        return "news"

    if any(w in text for w in [
        "hi", "hello", "hey", "what's up"
    ]):
        return "chat"

    return "question"



# -------------------------
# VOICE OUTPUT (CLEAN + NON-BLOCKING)
# -------------------------
def speak(text):
    try:
        # add natural pauses
        text = text.replace(".", "... ")
        text = text.replace(",", ", ")
        text = "Hmm... " + text  # conversational start

        safe_text = text.replace('"', '').replace('&', 'and')

        print("🔊 Speaking:", safe_text)

        cmd = f'echo {safe_text} | "{PIPER_PATH}" -m "{VOICE_PATH}" -f "{TEMP_AUDIO}"'
        subprocess.run(cmd, shell=True)

        # Play audio (blocking but reliable)
        subprocess.run(
            ["powershell", "-c", f"(New-Object Media.SoundPlayer '{TEMP_AUDIO}').PlaySync();"]
        )

    except Exception as e:
        print("⚠ Voice error:", e)
# -------------------------
# VOICE INPUT (STABLE)
# -------------------------
def listen():
    r = sr.Recognizer()

    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)

        try:
            audio = r.listen(source, timeout=20)
        except sr.WaitTimeoutError:
            return None

    try:
        return r.recognize_google(audio).lower()
    except:
        return None

# -------------------------
# MEMORY
# -------------------------
def load_memory():
    try:
        with open("memory.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"conversation_history": []}

def save_memory(memory):
    with open("memory.json", "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def update_memory(memory, user, response):
    memory["conversation_history"].append({
        "user": user,
        "saki": response
    })
    memory["conversation_history"] = memory["conversation_history"][-MAX_MEMORY:]
    save_memory(memory)

# -------------------------
# MODEL CALL
# -------------------------
def call_model(prompt):
    result = subprocess.run(
        ["ollama", "run", MODEL_FAST],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    output = result.stdout.strip()

    if not output or len(output) < 20:
        return None  # trigger search

    return output

# -------------------------
# PRIVACY-SAFE QUERY GENERATION
# -------------------------
def make_safe_query(user_input):
    """Convert input to neutral, general search query without personal details."""
    prompt = f"""
Convert this into a neutral, general search query.
Remove personal or sensitive details.

User input: {user_input}

Safe query:
"""
    result = call_model(prompt)
    return result.strip() if result else user_input

# -------------------------
# QUERY EXPANSION
# -------------------------
def expand_query(query):
    """Break query into 2 short search queries for better coverage."""
    prompt = f"""
Break this into 2 short search queries:

Query: {query}
"""
    result = call_model(prompt)

    if not result:
        return [query]

    lines = [l.strip() for l in result.split("\n") if l.strip()]
    return lines[:2]

    
# -------------------------
# CLEAN RESPONSE
# -------------------------
def clean_response(text):
    text = text.replace("As Saki", "")
    text = text.replace("Emotion:", "")

    lines = text.split("\n")
    clean = []

    for l in lines:
        if l.strip() and l.strip() not in clean:
            clean.append(l.strip())

    return " ".join(clean[:3])  # limit to short answer

# -------------------------
# ADD INTERACTION FEEL
# -------------------------
def add_personality(text):
    starters = [
        "Hmm... ",
        "Okay... ",
        "I see... ",
        "Interesting... "
    ]
    import random
    return random.choice(starters) + text

# -------------------------
# RESPONSE GENERATION
# -------------------------
def call_model_with(model, prompt):
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    return result.stdout.strip()


# -------------------------
# MAIN RESPONSE FUNCTION
# -------------------------
def generate_response(user_input):

    intent = detect_intent(user_input)

    # -------------------------
    # ❤️ EMOTIONAL → HERMES
    # -------------------------
    if intent == "emotional":
        prompt = f"""
You are a caring, supportive friend.

User: {user_input}

Respond with empathy, warmth, and understanding.
Keep it natural and comforting.
"""
        response = call_model_with(MODEL_EMO, prompt)
        return clean_response(response)

    # -------------------------
    # 📰 NEWS (PRIVACY-SAFE)
    # -------------------------
    elif intent == "news":
        news_data = get_news()

        prompt = f"""
User: {user_input}

News:
{news_data}

Summarize clearly in simple words.
"""
        response = call_model(prompt)
        return clean_response(response)

    # -------------------------
    # ⚡ PHI3 (CHAT + QUESTIONS)
    # -------------------------
    else:
        # style control
        if any(w in user_input for w in ["explain", "detail", "deep"]):
            style = "Explain clearly in a friendly way."
        else:
            style = "Reply in 2-3 short lines like a real conversation."

        prompt = f"""
You are a friendly AI assistant.

Rules:
- Talk like a human
- Be slightly warm
- Do NOT say "As an AI"
- Stay strictly on topic

User: {user_input}

Instruction:
{style}

Answer:
"""

        response = call_model(prompt)

        # -------------------------
        # 🌐 PRIVACY-SAFE FALLBACK SEARCH
        # -------------------------
        if not response or len(response.strip()) < 20 or any(x in response.lower() for x in [
            "i don't know", "not sure", "cannot answer"
        ]):
            # HIGH privacy → no search
            if PRIVACY_MODE == "HIGH":
                return "I prefer to stay private and answer based on what I know."

            print("🔐 Using privacy-safe search...")

            safe_query = make_safe_query(user_input)
            queries = expand_query(safe_query)

            search_results = []

            for q in queries:
                try:
                    search_results.extend(multi_search(q))
                except:
                    continue

            prompt = f"""
User question: {user_input}

Search results:
{search_results}

Give a clear and helpful answer.
"""
            response = call_model(prompt)

        return clean_response(response)


# -------------------------
# FOLLOW-UP (UNCHANGED)
# -------------------------
def follow_up(memory):
    prompt = f"""
User stopped talking.

Recent conversation:
{memory.get("conversation_history", [])[-2:]}

Ask ONE short friendly question.
"""
    return clean_response(call_model(prompt))

# -------------------------
# MAIN
# -------------------------
def main():
    print("Select Mode:")
    print("1 → Text Mode")
    print("2 → Voice Mode")

    mode = input("Enter choice: ").strip()

    memory = load_memory()
    last_time = time.time()
    idle_triggered = False

    print("\n🚀 Saki started...\n")

    while True:
        try:
            # -------------------------
            # TEXT MODE
            # -------------------------
            if mode == "1":
                user_input = input("\nYou: ").strip().lower()

                if user_input in ["exit", "quit", "bye"]:
                    print("👋 Goodbye!")
                    break

                response = add_personality(generate_response(user_input))
                print("\nSaki:", response)

                update_memory(memory, user_input, response)

            # -------------------------
            # VOICE MODE
            # -------------------------
            else:
                user_input = listen()

                # USER SPOKE
                if user_input:
                    print("🗣 You:", user_input)

                    if any(word in user_input for word in ["exit", "stop", "quit", "bye"]):
                        print("👋 Goodbye!")
                        speak("Okay... talk to you later.")
                        break

                    last_time = time.time()
                    idle_triggered = False

                    response = add_personality(generate_response(user_input))

                    print("🤖:", response)   # ALWAYS SHOW OUTPUT

                    # try speaking but don't break if it fails
                    try:
                        speak(response)
                    except Exception as e:
                        print("⚠ Voice failed:", e)
                    update_memory(memory, user_input, response)

                    time.sleep(1)

                # NO INPUT
                else:
                    time.sleep(2)

                    if not idle_triggered and (time.time() - last_time > IDLE_TIMEOUT):
                        follow = follow_up(memory)

                        speak(follow)
                        update_memory(memory, "silence", follow)

                        idle_triggered = True

                        time.sleep(3)

        except KeyboardInterrupt:
            print("\n👋 Stopped")
            continue


if __name__ == "__main__":
    main()