import json
import subprocess
import time

CHECK_INTERVAL = 120
INACTIVITY_THRESHOLD = 1800   # 30 min
LIGHT_IDLE_THRESHOLD = 600    # 10 min

FAST_MODEL = "phi3"
DEEP_MODEL = "nous-hermes2"


# -------------------------
# LOAD / SAVE
# -------------------------
def load_memory():
    with open("memory.json", encoding="utf-8") as f:
        return json.load(f)

def save_memory(memory):
    with open("memory.json", "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


# -------------------------
# STATE DETECTION
# -------------------------
def get_state(memory):
    last = memory.get("last_interaction_time", 0)
    diff = time.time() - last

    if diff < LIGHT_IDLE_THRESHOLD:
        return "active"
    elif diff < INACTIVITY_THRESHOLD:
        return "idle"
    else:
        return "inactive"


# -------------------------
# SMART WARMING
# -------------------------
def warm_model(model):
    try:
        subprocess.run(
            ["ollama", "generate", model],
            input="hi",
            capture_output=True,
            text=True,
            timeout=15
        )
    except:
        pass


def keep_models_smart(state):
    if state == "active":
        # user chatting → keep fast model ready
        warm_model(FAST_MODEL)

    elif state == "idle":
        # light idle → minimal warming
        warm_model(FAST_MODEL)

    elif state == "inactive":
        # do nothing → let models unload
        pass


# -------------------------
# PROACTIVE RESPONSE
# -------------------------
def generate_prompt(memory):
    return f"""
You are Saki, a caring human-like companion.

User:
Name: {memory.get("name")}
Mood: {memory.get("recent_mood")}

Recent chat:
{memory.get("conversation_history", [])[-2:]}

Talk naturally:
- check how user is doing
- be warm
- ask 1 thoughtful question
- keep it short
"""


def get_response(prompt):
    try:
        result = subprocess.run(
            ["ollama", "generate", FAST_MODEL],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout.strip()
    except:
        return "Hey… just checking in. How are you doing?"


# -------------------------
# MAIN LOOP
# -------------------------
def main():
    print("🧠 Optimized proactive system running...")

    while True:
        memory = load_memory()
        state = get_state(memory)

        # 🔥 smart resource usage
        keep_models_smart(state)

        # 🎯 trigger proactive only when inactive
        if state == "inactive":
            prompt = generate_prompt(memory)
            response = get_response(prompt)

            print("\n💬 Saki:", response)

            memory["last_interaction_time"] = time.time()
            save_memory(memory)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()