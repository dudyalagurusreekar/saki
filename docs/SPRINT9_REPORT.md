# Sprint 9: Real-Time Voice Interruption & Barge-In Report

## 1. Executive Summary

Sprint 9 completes the implementation and verification of **Real-Time Voice Interruption (Barge-In)** for Saki. Building directly upon the local voice pipeline established in Sprint 8 (Faster-Whisper STT, Kokoro-82M TTS, Silero-VAD, and Saki Event Manager), Saki is now capable of natural conversational barge-in: when the user speaks while Saki is speaking, Saki **immediately ceases audio playback (< 30ms)**, transitions cleanly to `LISTENING`, transcribes the user's new query, and seamlessly responds with full multi-turn conversational context preserved.

---

## 2. Architecture & Pipeline Lifecycle

### A. Non-Bifurcated Orchestration Flow

```
+-----------------------------------------------------------------------------------------+
|                                    USER SPEAKS                                          |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |         MicrophoneService (16kHz)           |
                      |   512-sample (32ms) audio streaming chunks  |
                      +---------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |             Silero-VAD Detector             |
                      |        Speech probability evaluated         |
                      +---------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |        InterruptionController (Debounce)    |
                      |  >= 3 consecutive speech chunks (~96-120ms) |
                      +---------------------------------------------+
                                             |
                                             v (Genuine speech detected while Saki speaking)
                      +---------------------------------------------+
                      |       AudioPlaybackManager.stop_playback()  |
                      |       tts_service.cancel_active_speech()    |
                      |   Instant hardware stop (< 30ms reaction)   |
                      +---------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |           SakiEventManager Emission         |
                      |   1. INTERRUPTION_DETECTED                  |
                      |   2. TTS_CANCELLED                          |
                      |   3. State Transition -> LISTENING          |
                      +---------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |           Faster-Whisper STT                |
                      |   Transcribes user interrupting utterance   |
                      +---------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |           Saki Brain & Chat Router          |
                      |   Qwen2.5 / DeepSeek / Hermes + Memory      |
                      +---------------------------------------------+
                                             |
                                             v
                      +---------------------------------------------+
                      |             Kokoro-82M TTS                  |
                      |   Synthesizes and speaks new response       |
                      +---------------------------------------------+
```

---

## 3. Core Components Implemented

### 1. `backend/services/interruption_controller.py`
- **Singleton `interruption_controller`** managing real-time speech onset evaluation, debounce state tracking, and sub-30ms TTS cancellation.
- **Configurable Debounce Filtering**:
  - `min_speech_duration_ms`: Default 120.0ms (~3-4 chunks).
  - `min_consecutive_chunks`: Default 3 chunks (3 x 32ms = 96ms).
  - `vad_threshold`: Default 0.5.
- **Noise Rejection**: Isolated mic bumps, clicks, or acoustic spikes (< 96ms) are discarded without interrupting Saki.
- **State Transition & Event Distribution**: Emits `INTERRUPTION_DETECTED` and `TTS_CANCELLED` events with detailed reaction latency telemetry and transitions `SakiState` to `LISTENING`.

### 2. `backend/services/tts_service.py` & `AudioPlaybackManager`
- **Hardware Native Audio Halting**: Integrates `sounddevice.stop()` and `winsound.PlaySound(None, winsound.SND_PURGE)` for instant audio buffer clearing.
- **Cancellation Latency**: Playback cancellation executes in `< 30ms` with zero trailing audio or buffer bleed.
- **Playback Progress Tracking**: Computes `(played_duration_sec, total_duration_sec)` and records `interrupted_at_sec` for context preservation.

### 3. `backend/services/microphone_service.py`
- **Real-Time VAD Chunk Evaluation**: Passes streaming chunks to `interruption_controller.evaluate_vad_chunk(...)` inside the dedicated worker loop.
- **Pre-Speech Ring Buffer Preservation**: 0.5-second pre-speech ring buffer ensures the initial syllable of user speech is retained for STT transcription.

### 4. `backend/services/voice_orchestrator.py`
- **Unified Turn Execution**: `VoiceTurnResult` tracks `interrupted: bool` and `interrupted_at_sec: float`.
- **Manual Interruption Hook**: `interrupt_active_turn()` allows programmatic or REST API barge-in triggering.

### 5. `backend/routes/voice.py` & REST API Schemas
- `POST /api/voice/interrupt`: Explicitly halts active speech synthesis and playback, transitioning Saki to `LISTENING`.
- `GET /api/voice/interruption/status`: Returns runtime debounce sensitivity and interruption telemetry.
- `POST /api/voice/interruption/config`: Dynamically adjusts debounce sensitivity and thresholds.

---

## 4. Empirical Benchmark Matrix Results

Empirical results captured via `tests/reliability/run_sprint9_interruption_matrix.py` and stored in `tests/reliability/sprint9_matrix_output.json`:

| Scenario ID | Scenario Description | STT Latency | Reaction Time | LLM Latency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Mid-Sentence Interruption** | User interrupts Saki halfway through answer | 315.2 ms | **< 30 ms** | 19,198 ms | **PASSED** |
| **2. Immediate Onset Interruption**| User interrupts Saki within 200ms of onset | 336.3 ms | **< 30 ms** | 3,698 ms | **PASSED** |
| **3. Normal Uninterrupted Turn** | Full conversational turn with no interruption | 284.8 ms | N/A | 26,425 ms | **PASSED** |
| **4. Multi-Turn Repeated Barge-In**| 3 consecutive rapid interruptions in 1 session| 336.2 ms (avg)| **< 30 ms** | 15,095 ms (avg)| **PASSED** |

### Resource Utilization Summary
- **Process Memory (RSS)**: 1,591.8 MB (Unified STT + TTS + VAD + Saki Backend)
- **Idle Process CPU%**: 0.0%
- **Interruption Reaction Latency**: **< 30ms** (Exceeds < 50ms requirement)

---

## 5. Automated Test Suite Results

Full automated testing was verified via `pytest`:

```
tests/reliability/test_sprint9_interruption.py:
  test_01_interruption_controller_initialization_and_config ........... PASSED [  8%]
  test_02_instant_tts_playback_cancellation ........................... PASSED [ 16%]
  test_03_debounce_and_short_noise_rejection .......................... PASSED [ 25%]
  test_04_genuine_speech_triggers_interruption_and_tts_cancelled_events PASSED [ 33%]
  test_05_mid_sentence_barge_in_turn_execution ........................ PASSED [ 41%]
  test_06_immediate_speech_onset_interruption ......................... PASSED [ 50%]
  test_07_uninterrupted_normal_voice_turn ............................. PASSED [ 58%]
  test_08_rapid_repeated_consecutive_interruptions .................... PASSED [ 66%]
  test_09_race_condition_saki_finishing_at_speech_onset ............... PASSED [ 75%]
  test_10_memory_and_conversation_context_continuity_after_interruption PASSED [ 83%]
  test_11_text_chat_independence ...................................... PASSED [ 91%]
  test_12_fastapi_interruption_endpoints .............................. PASSED [100%]

============================= 12 passed in 152.66s =============================

tests/reliability/test_sprint8_voice_pipeline.py (Regression Suite):
  test_01 through test_12 ............................................. PASSED [100%]

============================= 12 passed in 233.53s =============================
```

**Total Pass Rate**: **24/24 (100%)**
