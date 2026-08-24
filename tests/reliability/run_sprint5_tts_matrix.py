"""
Sprint 5 Manual TTS Evaluation & Voice Benchmark Matrix Runner
Benchmarks all 5 selected local English female voices across standardized Saki response categories,
measuring first-chunk latency, total synthesis time, duration, RTF, CPU%, RAM, and saving structured results.
"""

import os
import sys
import json
import time
from typing import Dict, List, Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.tts_service import tts_service, KokoroTTSProvider

MATRIX_PROMPTS = [
    {
        "id": "casual_greeting",
        "category": "Casual Greeting",
        "text": "Hey! Good to see you. What are we building or exploring today? 🌸"
    },
    {
        "id": "empathetic_support",
        "category": "Empathetic Support",
        "text": "I'm right here with you. Take a breath, we can solve this together step by step."
    },
    {
        "id": "technical_reasoning",
        "category": "Technical Reasoning",
        "text": "The asynchronous event loop handles concurrent network streams without blocking the main execution thread."
    },
    {
        "id": "enthusiastic_action",
        "category": "Enthusiastic Action",
        "text": "That looks amazing! Let me run the build pipeline and test the changes right now."
    }
]

TARGET_VOICES = [
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky"
]


def run_matrix() -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print("   SAKI SPRINT 5: LOCAL ENGLISH FEMALE TTS BENCHMARK & EVALUATION MATRIX")
    print("=" * 80 + "\n")

    prov = tts_service.kokoro
    if not prov.initialize():
        print(f"ERROR: Kokoro TTS failed to initialize: {prov.get_status().get('error')}")
        return {"error": prov.get_status().get('error')}

    status = prov.get_status()
    print(f"Model: {status['model_path']} ({status['model_size_mb']} MB)")
    print(f"Voices: {status['voices_path']} ({status['voices_size_mb']} MB)")
    print(f"Device: {status['device'].upper()} | Sample Rate: {status['sample_rate']} Hz | License: {status['license']}")
    print("-" * 80 + "\n")

    # Warmup turn
    print("Executing warmup turn...")
    tts_service.synthesize_response("Warmup test.", voice="af_heart")
    print("Warmup complete.\n")

    matrix_results: Dict[str, List[Dict[str, Any]]] = {v: [] for v in TARGET_VOICES}
    voice_averages: Dict[str, Dict[str, float]] = {}

    for v_idx, voice in enumerate(TARGET_VOICES, 1):
        traits = KokoroTTSProvider.VOICE_PERSONAS.get(voice, {})
        print(f"[{v_idx}/{len(TARGET_VOICES)}] Benchmarking Voice: [{voice}] — {traits.get('tone', '')}")

        total_lat = 0.0
        total_dur = 0.0
        total_rtf = 0.0
        total_chars = 0
        total_cpu = 0.0
        total_ram = 0.0
        runs = 0

        for prompt in MATRIX_PROMPTS:
            t0 = time.time()
            res = tts_service.synthesize_response(prompt["text"], voice=voice, speed=1.0)
            elapsed = time.time() - t0

            item = {
                "prompt_id": prompt["id"],
                "category": prompt["category"],
                "text": prompt["text"],
                "character_count": res.character_count,
                "word_count": res.word_count,
                "duration_seconds": round(res.duration_seconds, 3),
                "latency_ms": round(res.latency_ms, 2),
                "first_chunk_latency_ms": round(res.first_chunk_latency_ms, 2),
                "rtf": round(res.rtf, 3),
                "cpu_percent": round(res.cpu_percent, 1),
                "memory_mb": round(res.memory_mb, 1),
                "audio_bytes_size": len(res.audio_bytes)
            }
            matrix_results[voice].append(item)

            total_lat += res.latency_ms
            total_dur += res.duration_seconds
            total_rtf += res.rtf
            total_chars += res.character_count
            total_cpu += res.cpu_percent
            total_ram += res.memory_mb
            runs += 1

            speedup = round(1.0 / res.rtf, 1) if res.rtf > 0 else 0
            print(f"   [{prompt['category']}] Latency: {res.latency_ms:.1f}ms | Dur: {res.duration_seconds:.2f}s | RTF: {res.rtf:.3f}x ({speedup}x real-time) | RAM: {res.memory_mb:.1f}MB")

        if runs > 0:
            voice_averages[voice] = {
                "avg_latency_ms": round(total_lat / runs, 2),
                "avg_duration_sec": round(total_dur / runs, 2),
                "avg_rtf": round(total_rtf / runs, 3),
                "avg_cpu_percent": round(total_cpu / runs, 1),
                "avg_memory_mb": round(total_ram / runs, 1),
                "total_chars_tested": total_chars
            }
        print()

    output_payload = {
        "engine": "Kokoro-82M ONNX",
        "sample_rate": 24000,
        "selected_default_voice": "af_heart",
        "status": status,
        "results_by_voice": matrix_results,
        "voice_averages": voice_averages,
        "timestamp": time.time()
    }

    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "sprint5_tts_matrix_output.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("=" * 80)
    print(f"Matrix run complete! Saved results to: {out_file}")
    print("=" * 80 + "\n")

    return output_payload


if __name__ == "__main__":
    run_matrix()
