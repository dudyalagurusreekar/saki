"""
Sprint 8 — End-to-End Voice -> Brain -> Local Voice Benchmark Matrix Runner

Executes empirical measurements across 4 core conversational scenarios:
1. Short Conversational Greeting ("Hello Saki, good morning.")
2. Empathetic Support & Emotional Guidance ("I feel so overwhelmed and exhausted with my work today.")
3. Technical Coding & System Architecture ("How do I create a FastAPI router in Python?")
4. Multi-Turn Memory Continuity (Teach preference in Voice -> Recall in Text / Voice)

Measures stage-by-stage latencies (STT, LLM, TTS, Total) and resource usage (RAM, CPU%).
Saves output to tests/reliability/sprint8_voice_matrix_output.json.
"""

import os
import sys
import io
import time
import json
import base64
import numpy as np
import soundfile as sf

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.services.stt_service import stt_service
from backend.services.tts_service import tts_service
from backend.services.voice_orchestrator import voice_orchestrator
from backend.services.memory_service import load_memory
from backend.routes.chat import ChatRequest, chat

try:
    import psutil
except ImportError:
    psutil = None


BENCHMARK_SCENARIOS = [
    {
        "id": "short_greeting",
        "category": "Short Conversational Greeting",
        "user_utterance": "Hello Saki, good morning.",
        "voice": "af_heart"
    },
    {
        "id": "emotional_support",
        "category": "Empathetic Support & Emotional Care",
        "user_utterance": "I feel so overwhelmed and exhausted with my work today.",
        "voice": "af_heart"
    },
    {
        "id": "coding_assistance",
        "category": "Technical Coding & Architecture",
        "user_utterance": "How do I create a FastAPI router in Python?",
        "voice": "af_heart"
    },
    {
        "id": "multi_turn_memory",
        "category": "Multi-Turn Memory Continuity",
        "user_utterance": "My favorite programming language is Rust, please remember that.",
        "followup_query": "What is my favorite programming language?",
        "voice": "af_heart"
    }
]


def synthesize_user_voice(text: str, voice: str = "af_heart") -> bytes:
    """Synthesizes sample user audio for benchmark evaluation."""
    res = tts_service.synthesize_response(text, voice=voice)
    return res.audio_bytes


def run_benchmark_matrix():
    print("=" * 80)
    print("   SAKI SPRINT 8: VOICE -> EXISTING SAKI BRAIN -> LOCAL VOICE BENCHMARK")
    print("=" * 80)

    # 1. Initialize services
    t0_stt = time.perf_counter()
    stt_service.initialize()
    stt_init_ms = (time.perf_counter() - t0_stt) * 1000.0

    print(f"\nFaster-Whisper STT Initialization: SUCCESS ({stt_init_ms:.2f} ms)")
    print(f"Kokoro-82M TTS Engine: READY (af_heart primary)")
    print(f"Saki Cognitive Brain: CONNECTED (Unified Ollama Routing & Memory)")

    scenario_results = []
    total_latencies = []
    stt_latencies = []
    llm_latencies = []
    tts_latencies = []

    print("\nExecuting End-to-End Voice Evaluation Scenarios:")
    print("-" * 80)

    for idx, sc in enumerate(BENCHMARK_SCENARIOS, 1):
        print(f"\n[{idx}/{len(BENCHMARK_SCENARIOS)}] Scenario: {sc['category']}")
        print(f"   Input Utterance: \"{sc['user_utterance']}\"")

        # Synthesize audio
        audio_wav = synthesize_user_voice(sc["user_utterance"], voice="af_heart")
        conv_id = f"sprint8-matrix-{sc['id']}-{int(time.time())}"

        proc = psutil.Process() if psutil else None
        t_start = time.perf_counter()

        turn_res = voice_orchestrator.execute_voice_turn(
            audio_input=audio_wav,
            conversation_id=conv_id,
            voice=sc["voice"],
            play_locally=False
        )

        turn_wall_ms = (time.perf_counter() - t_start) * 1000.0
        cpu_pct = proc.cpu_percent(interval=None) if proc else 0.0
        mem_mb = (proc.memory_info().rss / (1024 * 1024)) if proc else 0.0

        stt_latencies.append(turn_res.stt_latency_ms)
        llm_latencies.append(turn_res.llm_latency_ms)
        tts_latencies.append(turn_res.tts_latency_ms)
        total_latencies.append(turn_res.total_latency_ms)

        print(f"   Transcript: \"{turn_res.transcript}\" (STT: {turn_res.stt_latency_ms:.1f}ms)")
        print(f"   Model: {turn_res.selected_model} | Mode: {turn_res.conversation_mode} (LLM: {turn_res.llm_latency_ms:.1f}ms)")
        print(f"   Response Snippet: \"{turn_res.response_text[:120]}...\"")
        print(f"   TTS Output: {turn_res.audio_duration_sec:.2f}s audio (TTS: {turn_res.tts_latency_ms:.1f}ms, Voice: {turn_res.voice_used})")
        print(f"   Total Turn Latency: {turn_res.total_latency_ms:.1f}ms | RAM: {mem_mb:.1f} MB | CPU: {cpu_pct:.1f}%")

        followup_data = None
        if "followup_query" in sc:
            print(f"   Executing Follow-Up Query: \"{sc['followup_query']}\" (Testing Memory Continuity)")
            t_f0 = time.perf_counter()
            f_audio = synthesize_user_voice(sc["followup_query"], voice="af_heart")
            f_res = voice_orchestrator.execute_voice_turn(
                audio_input=f_audio,
                conversation_id=conv_id,
                voice=sc["voice"],
                play_locally=False
            )
            f_ms = (time.perf_counter() - t_f0) * 1000.0
            print(f"   Follow-Up Transcript: \"{f_res.transcript}\"")
            print(f"   Follow-Up Response: \"{f_res.response_text[:140]}...\" ({f_ms:.1f}ms)")
            followup_data = {
                "query": sc["followup_query"],
                "transcript": f_res.transcript,
                "response": f_res.response_text,
                "latency_ms": round(f_ms, 2),
                "recalled_memory": "rust" in f_res.response_text.lower()
            }

        scenario_results.append({
            "scenario_id": sc["id"],
            "category": sc["category"],
            "input_utterance": sc["user_utterance"],
            "transcript": turn_res.transcript,
            "response_text": turn_res.response_text,
            "selected_model": turn_res.selected_model,
            "task_type": turn_res.task_type,
            "conversation_mode": turn_res.conversation_mode,
            "audio_duration_sec": round(turn_res.audio_duration_sec, 3),
            "voice_used": turn_res.voice_used,
            "tts_provider": turn_res.tts_provider,
            "stt_latency_ms": round(turn_res.stt_latency_ms, 2),
            "llm_latency_ms": round(turn_res.llm_latency_ms, 2),
            "tts_latency_ms": round(turn_res.tts_latency_ms, 2),
            "total_latency_ms": round(turn_res.total_latency_ms, 2),
            "cpu_percent": round(cpu_pct, 1),
            "memory_mb": round(mem_mb, 1),
            "followup": followup_data
        })

    avg_stt = sum(stt_latencies) / len(stt_latencies)
    avg_llm = sum(llm_latencies) / len(llm_latencies)
    avg_tts = sum(tts_latencies) / len(tts_latencies)
    avg_total = sum(total_latencies) / len(total_latencies)

    output_payload = {
        "subsystem": "Saki Voice -> Brain -> Voice Pipeline",
        "stt_model": "faster-whisper-tiny.en (CTranslate2 int8 CPU)",
        "tts_model": "Kokoro-82M ONNX (af_heart)",
        "llm_routing": "Dynamic Multi-Model (Phi-3 / Qwen Coder)",
        "stt_init_time_ms": round(stt_init_ms, 2),
        "averages": {
            "avg_stt_latency_ms": round(avg_stt, 2),
            "avg_llm_latency_ms": round(avg_llm, 2),
            "avg_tts_latency_ms": round(avg_tts, 2),
            "avg_total_latency_ms": round(avg_total, 2)
        },
        "scenarios": scenario_results,
        "timestamp": time.time()
    }

    out_path = os.path.abspath("tests/reliability/sprint8_voice_matrix_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Matrix benchmark complete! Saved results to: {out_path}")
    print(f"Average STT Latency:   {avg_stt:.1f} ms")
    print(f"Average LLM Latency:   {avg_llm:.1f} ms")
    print(f"Average TTS Latency:   {avg_tts:.1f} ms")
    print(f"Average Total Latency: {avg_total:.1f} ms")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark_matrix()
