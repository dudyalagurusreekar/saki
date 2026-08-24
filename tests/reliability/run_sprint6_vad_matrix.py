"""
Sprint 6 — Local Microphone & Silero VAD Benchmark Matrix Runner

Executes comprehensive empirical measurements for:
1. Silero VAD Neural Model initialization time and memory footprint
2. Detection latency per 512-sample (32ms) 16kHz chunk
3. Speech onset/offset boundary detection across 4 realistic speech scenarios
4. Audio input device enumeration and capabilities
5. CPU% and RAM RSS consumption during continuous VAD processing

Saves JSON output to tests/reliability/sprint6_vad_matrix_output.json.
"""

import os
import sys
import io
import time
import json
import numpy as np
import soundfile as sf

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.microphone_service import (
    microphone_service,
    SileroVADDetector,
    float32_to_wav_bytes
)
from backend.services.tts_service import tts_service

try:
    import psutil
except ImportError:
    psutil = None


BENCHMARK_PROMPTS = [
    {
        "id": "short_greeting",
        "category": "Short Conversational Greeting",
        "text": "Hello Saki, good morning."
    },
    {
        "id": "quick_query",
        "category": "Quick Technical Query",
        "text": "What is the status of our current project build?"
    },
    {
        "id": "multi_sentence_query",
        "category": "Multi-Sentence Detailed Utterance",
        "text": "Can you check if the event system is connected properly and tell me how the state transitions work?"
    },
    {
        "id": "rapid_command",
        "category": "Rapid Short Directive",
        "text": "Run the tests right now."
    }
]


def run_benchmark_matrix():
    print("=" * 80)
    print("   SAKI SPRINT 6: LOCAL MICROPHONE + SILERO VAD BENCHMARK MATRIX")
    print("=" * 80)

    # 1. Initialize VAD Detector
    vad = SileroVADDetector(threshold=0.5, min_silence_duration_ms=400)
    t0_init = time.perf_counter()
    vad_ok = vad.initialize()
    init_time_ms = (time.perf_counter() - t0_init) * 1000.0

    print(f"\nSilero VAD Initialization: {'SUCCESS' if vad_ok else 'FAILED'} ({init_time_ms:.2f} ms)")
    print(f"Sample Rate: 16000 Hz | Chunk Size: 512 samples (32.0 ms)")

    # 2. Enumerate Input Devices
    devices = microphone_service.list_devices()
    print(f"\nDetected Input Audio Devices ({len(devices)} total):")
    for d in devices[:5]: # print top 5
        print(f"  [{d['id']}] {d['name']} (Channels: {d['channels']}, Default: {d['is_default']})")

    # 3. Benchmark VAD Processing across scenarios
    scenario_results = []
    chunk_latencies = []

    print("\nExecuting Speech Evaluation Scenarios:")
    print("-" * 80)

    for idx, prompt in enumerate(BENCHMARK_PROMPTS, 1):
        print(f"\n[{idx}/{len(BENCHMARK_PROMPTS)}] Scenario: {prompt['category']}")
        print(f"   Input Text: \"{prompt['text']}\"")

        # Synthesize real speech from Kokoro
        tts_res = tts_service.synthesize_response(prompt["text"], voice="af_heart")
        audio_data, sr = sf.read(io.BytesIO(tts_res.audio_bytes), dtype="float32")

        # Resample to 16kHz
        target_len = int(len(audio_data) * 16000 / float(sr))
        audio_16k = np.interp(
            np.linspace(0, len(audio_data), target_len, endpoint=False),
            np.arange(len(audio_data)),
            audio_data
        ).astype(np.float32)

        # Pad with 0.5s leading silence and 1.0s trailing silence
        leading_silence = np.zeros(8000, dtype=np.float32)
        trailing_silence = np.zeros(16000, dtype=np.float32)
        stream_16k = np.concatenate([leading_silence, audio_16k, trailing_silence])
        total_dur_sec = len(stream_16k) / 16000.0
        speech_dur_sec = len(audio_16k) / 16000.0

        vad.reset_state()
        chunk_size = 512
        events = []
        scenario_latencies = []
        speech_chunk_count = 0

        proc = psutil.Process() if psutil else None
        t_start = time.perf_counter()

        for i in range(0, len(stream_16k) - chunk_size, chunk_size):
            chunk = stream_16k[i:i+chunk_size]
            t_chunk_0 = time.perf_counter()
            prob, vad_ev = vad.process_chunk(chunk)
            t_chunk_ms = (time.perf_counter() - t_chunk_0) * 1000.0
            scenario_latencies.append(t_chunk_ms)
            chunk_latencies.append(t_chunk_ms)

            if prob >= vad.threshold:
                speech_chunk_count += 1
            if vad_ev:
                events.append({
                    "timestamp_sec": round(i / 16000.0, 3),
                    "event": vad_ev
                })

        total_proc_time_ms = (time.perf_counter() - t_start) * 1000.0
        avg_chunk_ms = sum(scenario_latencies) / len(scenario_latencies)
        cpu_pct = proc.cpu_percent(interval=None) if proc else 0.0
        mem_mb = (proc.memory_info().rss / (1024 * 1024)) if proc else 0.0

        print(f"   Audio Duration: {total_dur_sec:.2f}s (Speech: {speech_dur_sec:.2f}s)")
        print(f"   VAD Total Processing Time: {total_proc_time_ms:.2f} ms ({len(scenario_latencies)} chunks)")
        print(f"   Avg Neural Latency per Chunk: {avg_chunk_ms:.3f} ms (Min: {min(scenario_latencies):.3f}ms, Max: {max(scenario_latencies):.3f}ms)")
        print(f"   Detected Events: {events}")
        print(f"   RAM: {mem_mb:.1f} MB | CPU: {cpu_pct:.1f}%")

        scenario_results.append({
            "prompt_id": prompt["id"],
            "category": prompt["category"],
            "text": prompt["text"],
            "total_audio_duration_sec": round(total_dur_sec, 3),
            "actual_speech_duration_sec": round(speech_dur_sec, 3),
            "chunks_processed": len(scenario_latencies),
            "speech_chunks_detected": speech_chunk_count,
            "total_processing_time_ms": round(total_proc_time_ms, 2),
            "avg_chunk_latency_ms": round(avg_chunk_ms, 3),
            "min_chunk_latency_ms": round(min(scenario_latencies), 3),
            "max_chunk_latency_ms": round(max(scenario_latencies), 3),
            "events_detected": events,
            "cpu_percent": round(cpu_pct, 1),
            "memory_mb": round(mem_mb, 1)
        })

    # Summary calculations
    overall_avg_chunk_latency = sum(chunk_latencies) / len(chunk_latencies) if chunk_latencies else 0.0

    output_data = {
        "subsystem": "Saki Local Microphone & Silero VAD",
        "vad_model": "Silero-VAD-v5",
        "sample_rate": 16000,
        "chunk_size_samples": 512,
        "chunk_duration_ms": 32.0,
        "initialization_time_ms": round(init_time_ms, 2),
        "overall_avg_chunk_latency_ms": round(overall_avg_chunk_latency, 3),
        "detected_devices_count": len(devices),
        "input_devices": devices,
        "scenarios": scenario_results,
        "timestamp": time.time()
    }

    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "sprint6_vad_matrix_output.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Matrix benchmark complete! Saved results to: {out_file}")
    print(f"Overall Average Neural Inference Latency per 32ms Chunk: {overall_avg_chunk_latency:.3f} ms")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_benchmark_matrix()
