"""
Saki Context-Aware Proactive Intelligence Engine
Monitors conversational state, idle duration, emotional context, and ongoing projects
to decide if and when a warm, natural check-in is helpful—respecting comfortable silence.
"""

import time
import subprocess
from typing import Tuple, Optional
from backend.services.memory_service import load_memory, save_memory
from backend.core.saki_persona import build_saki_system_prompt
from backend.core.config import settings

CHECK_INTERVAL = 60  # Check every 60 seconds
MIN_SILENCE_THRESHOLD = 600   # 10 minutes minimum before considering check-in
MAX_SILENCE_THRESHOLD = 7200  # 2 hours maximum (after which user has likely stepped away)

FAST_MODEL = settings.MODEL_PHI3


def should_proactively_speak(memory: dict) -> Tuple[bool, str]:
    """
    Intelligent silence evaluation matrix:
    - Was Saki asking a question?
    - Is user in an active/recent conversation?
    - Is a follow-up genuinely useful?
    - Would an interruption be annoying?
    """
    last_time = memory.get("last_interaction_time")
    if not last_time:
        return False, "No prior interactions."

    silence_duration = time.time() - float(last_time)

    # 1. Too early to speak
    if silence_duration < MIN_SILENCE_THRESHOLD:
        return False, f"Recent interaction ({int(silence_duration)}s ago). Saki remains comfortable in silence."

    # 2. Stepped away for hours
    if silence_duration > MAX_SILENCE_THRESHOLD:
        return False, "User has stepped away for an extended period. Staying silent."

    # 3. Analyze last interaction
    history = memory.get("conversation_history", [])
    if not history:
        return False, "No conversation history."

    last_turn = history[-1]
    last_saki = last_turn.get("saki", "").strip()
    last_user = last_turn.get("user", "").strip()

    awareness = memory.get("awareness", {})
    emotional_state = awareness.get("emotional_state", {})
    last_emotion = emotional_state.get("emotion", "neutral")
    current_project = awareness.get("current_project", "Saki")
    activity = awareness.get("current_activity", "chatting")

    # If user was frustrated / debugging and silence has been 15-25 mins
    if last_emotion == "frustrated" and silence_duration >= 900:
        return True, "User was frustrated debugging earlier. A gentle, calming check-in is helpful."

    # If user was sad or overwhelmed
    if last_emotion in ["sad", "overwhelmed"] and silence_duration >= 900:
        return True, "User was feeling down earlier. A warm, quiet check-in shows genuine care."

    # If Saki asked a specific question and user paused for 10-15 mins
    if last_saki.endswith("?") and silence_duration >= 600:
        return True, "Following up gently on previous question."

    # If active project was being worked on and user went silent for 20 mins
    if activity == "coding" and silence_duration >= 1200:
        return True, f"Checking in quietly on {current_project} progress."

    return False, "Comfortable silence; no interruption needed."


def generate_proactive_checkin(memory: dict) -> str:
    """Generates a short, natural check-in using Saki's unified persona."""
    awareness = memory.get("awareness", {})
    project = awareness.get("current_project", "Saki")
    history = memory.get("conversation_history", [])[-2:]
    
    prompt = f"""You are Saki. You are checking in quietly on your companion after some silence.
Active project: {project}
Recent context: {history}

Rules:
- Keep it to 1 short, warm, natural sentence.
- NO robotic phrases ("How can I assist you?", "Just checking in on you").
- Speak like a caring friend sitting nearby in the room.

Saki:"""

    try:
        res = subprocess.run(
            ["ollama", "run", FAST_MODEL],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = res.stdout.strip()
        if output:
            return output
    except Exception as e:
        print(f"Error generating proactive checkin: {e}")

    return f"Still thinking through the {project} piece, or taking a breather? ☕"


def main():
    print("🌸 Saki Context-Aware Proactive Intelligence running...")

    while True:
        try:
            memory = load_memory()
            should_speak, reason = should_proactively_speak(memory)

            if should_speak:
                print(f"\n[Proactive Trigger]: {reason}")
                checkin = generate_proactive_checkin(memory)
                print(f"💬 Saki: {checkin}")

                memory["conversation_history"].append({"user": "[Silence / Pause]", "saki": checkin})
                memory["last_interaction_time"] = time.time()
                save_memory(memory)
        except Exception as e:
            print(f"Proactive loop error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()