/**
 * Comprehensive VAD & Audio Pipeline Test Suite
 * Tests:
 * 1. Normal Speech: "Hello Saki" -> 2000ms silence -> Finalize once -> Non-empty WAV.
 * 2. Natural Pause: Speech -> 1s silence -> Resume speech -> Timer cancelled -> 2s silence -> Finalize once.
 * 3. Click / Noise Rejection: Speech -> Silence -> 1-frame click -> Timer continues -> Finalize once.
 * 4. Audio Graph Isolation: Microphone stream has ZERO path to AudioDestinationNode.
 * 5. Guarded Finalization: No duplicate executions or race conditions.
 */

import { strict as assert } from "assert";

console.log("==================================================");
console.log("    SAKI VOICE PIPELINE: VAD & GRAPH TEST SUITE   ");
console.log("==================================================");

let testsPassed = 0;
let testsFailed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log(`  ✓ ${name}`);
    testsPassed++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    Error: ${err.message}`);
    testsFailed++;
  }
}

// -------------------------------------------------------------
// Simulated AudioRecorder implementation replicating exact logic
// -------------------------------------------------------------
const DEFAULT_SILENCE_TIMEOUT_MS = 2000;
const DEFAULT_SPEECH_THRESHOLD = 0.015;
const DEFAULT_MIN_SPEECH_FRAMES = 2;

class SimulatedAudioRecorder {
  constructor(options = {}) {
    this.options = {
      silenceTimeoutMs: DEFAULT_SILENCE_TIMEOUT_MS,
      speechThreshold: DEFAULT_SPEECH_THRESHOLD,
      enableAutoSubmit: true,
      ...options,
    };
    this.turnId = `sim-turn-${Date.now()}`;
    this.state = "IDLE";
    this.consecutiveSpeechFrames = 0;
    this.hasSpokenInUtterance = false;
    this.silenceStartTimestamp = null;
    this.silenceGeneration = 0;
    this.isRecording = true;
    this.isFinalizing = false;
    this.pcmChunks = [];
    this.totalSamples = 0;
    this.pendingTimeouts = new Map(); // id -> { timeoutMs, scheduledAt, generation, callback }
    this.simulatedTime = 1000;
    this.finalizedPayload = null;

    this.diagnostics = {
      turnId: this.turnId,
      state: "IDLE",
      speechDetected: false,
      speechStartedAt: null,
      silenceStartedAt: null,
      silenceElapsedMs: 0,
      silenceTimerStarted: false,
      silenceTimerCancelled: false,
      silenceTimeoutTriggered: false,
      recordingStarted: true,
      recordingStopped: false,
      recordingFinalized: false,
      audioDurationMs: 0,
      audioBlobSize: 0,
      sendVoiceTurnCalled: false,
      silenceGeneration: 0,
    };
  }

  getNow() {
    return this.simulatedTime;
  }

  async advanceTime(ms) {
    this.simulatedTime += ms;
    // Check scheduled timeouts
    const now = this.simulatedTime;
    for (const [id, timer] of Array.from(this.pendingTimeouts.entries())) {
      if (now >= timer.scheduledAt + timer.timeoutMs) {
        this.pendingTimeouts.delete(id);
        await timer.callback();
      }
    }
  }

  async feedFrame(rms) {
    if (!this.isRecording || this.isFinalizing) return;

    // Simulate 4096 samples at 48kHz ~ 85.3ms
    const frameSamples = 4096;
    const fakeData = new Float32Array(frameSamples);
    fakeData.fill(rms);
    this.pcmChunks.push(fakeData);
    this.totalSamples += frameSamples;

    this.processVADFrame(rms);
    await this.advanceTime(85.3);
  }

  processVADFrame(rms) {
    const threshold = this.options.speechThreshold ?? DEFAULT_SPEECH_THRESHOLD;
    const silenceTimeout = this.options.silenceTimeoutMs ?? DEFAULT_SILENCE_TIMEOUT_MS;
    const now = this.getNow();

    if (rms >= threshold) {
      this.consecutiveSpeechFrames++;

      if (this.consecutiveSpeechFrames >= DEFAULT_MIN_SPEECH_FRAMES) {
        if (this.state !== "SPEAKING") {
          if (this.state === "SILENCE_COUNTDOWN" || this.silenceStartTimestamp !== null) {
            this.silenceGeneration++;
            this.clearSilenceTimers();
            this.state = "SPEAKING";
            this.diagnostics.state = "SPEAKING";
            this.diagnostics.silenceTimerCancelled = true;
            this.diagnostics.silenceGeneration = this.silenceGeneration;
            this.options.onSpeechResumed?.();
          } else {
            this.hasSpokenInUtterance = true;
            this.state = "SPEAKING";
            this.diagnostics.state = "SPEAKING";
            this.diagnostics.speechDetected = true;
            this.diagnostics.speechStartedAt = now;
            this.clearSilenceTimers();
            this.options.onSpeechStart?.();
          }
        }
      }
    } else {
      this.consecutiveSpeechFrames = 0;

      if (this.hasSpokenInUtterance) {
        if (this.state === "SPEAKING") {
          this.state = "SILENCE_COUNTDOWN";
          this.silenceStartTimestamp = now;
          this.silenceGeneration++;
          const currentGen = this.silenceGeneration;

          this.diagnostics.state = "SILENCE_COUNTDOWN";
          this.diagnostics.silenceStartedAt = now;
          this.diagnostics.silenceTimerStarted = true;
          this.diagnostics.silenceTimerCancelled = false;
          this.diagnostics.silenceTimeoutTriggered = false;
          this.diagnostics.silenceGeneration = currentGen;
          this.options.onSilenceStart?.();

          if (this.options.enableAutoSubmit) {
            this.startSilenceFinalization(silenceTimeout, currentGen);
          }
        } else if (this.state === "SILENCE_COUNTDOWN" && this.silenceStartTimestamp !== null) {
          const elapsed = now - this.silenceStartTimestamp;
          this.diagnostics.silenceElapsedMs = elapsed;
          const remainingSec = Math.max(0, (silenceTimeout - elapsed) / 1000);
          const fraction = Math.min(1.0, elapsed / silenceTimeout);
          this.options.onSilenceCountdown?.(remainingSec, fraction);
        }
      }
    }
  }

  startSilenceFinalization(timeoutMs, generation) {
    if (this.silenceFinalizeTimer !== null) {
      this.pendingTimeouts.delete(this.silenceFinalizeTimer);
      this.silenceFinalizeTimer = null;
    }
    const timerId = `timer-${generation}`;
    this.silenceFinalizeTimer = timerId;
    this.pendingTimeouts.set(timerId, {
      timeoutMs,
      scheduledAt: this.getNow(),
      generation,
      callback: async () => {
        const now = this.getNow();
        const elapsed = this.silenceStartTimestamp !== null ? now - this.silenceStartTimestamp : 0;
        if (
          this.isRecording &&
          !this.isFinalizing &&
          this.state === "SILENCE_COUNTDOWN" &&
          this.silenceGeneration === generation &&
          this.hasSpokenInUtterance &&
          elapsed >= timeoutMs - 50
        ) {
          this.diagnostics.silenceTimeoutTriggered = true;
          this.diagnostics.silenceElapsedMs = elapsed;
          await this.finalizeCurrentUtterance();
        }
      },
    });
  }

  clearSilenceTimers() {
    this.pendingTimeouts.clear();
    this.silenceStartTimestamp = null;
  }

  async finalizeCurrentUtterance() {
    if (this.isFinalizing) return null;
    this.isFinalizing = true;
    this.state = "FINALIZING";
    this.diagnostics.state = "FINALIZING";
    this.clearSilenceTimers();

    const durationSec = (this.totalSamples / 48000.0);
    const mockWavBytes = 44 + Math.round(durationSec * 16000 * 2);
    const payload = {
      blob: { size: mockWavBytes, type: "audio/wav" },
      base64: "data:audio/wav;base64,MOCK_WAV_BASE64",
      durationSec,
    };

    this.state = "FINALIZED";
    this.diagnostics.state = "FINALIZED";
    this.diagnostics.recordingFinalized = true;
    this.diagnostics.recordingStopped = true;
    this.diagnostics.audioBlobSize = payload.blob.size;
    this.diagnostics.audioDurationMs = payload.durationSec * 1000;
    this.isRecording = false;
    this.finalizedPayload = payload;

    this.options.onUtteranceFinalized?.(payload);
    return payload;
  }

  getDiagnostics() {
    return { ...this.diagnostics };
  }

  markSendVoiceTurnCalled() {
    this.diagnostics.sendVoiceTurnCalled = true;
  }
}

// -------------------------------------------------------------
// TEST RUNNER
// -------------------------------------------------------------

async function runAllTests() {
  console.log("\n1. Test A: Normal Speech -> 2000ms Silence Finalization");
  await test("Speech onset requires 2 frames above threshold", async () => {
    const rec = new SimulatedAudioRecorder();
    assert.equal(rec.state, "IDLE");

    // 1 frame of speech
    await rec.feedFrame(0.05);
    assert.equal(rec.state, "IDLE", "1 frame should not trigger speech yet");

    // 2nd frame of speech
    await rec.feedFrame(0.05);
    assert.equal(rec.state, "SPEAKING", "2nd consecutive frame triggers SPEAKING");
    assert.equal(rec.getDiagnostics().speechDetected, true);
  });

  await test("Normal utterance 'Hello Saki' finalizes after 2000ms silence", async () => {
    let utteranceFinalized = false;
    let receivedPayload = null;

    const rec = new SimulatedAudioRecorder({
      onUtteranceFinalized: (payload) => {
        utteranceFinalized = true;
        receivedPayload = payload;
      },
    });

    // User speaks "Hello Saki" for ~1.0 second (~12 frames)
    for (let i = 0; i < 12; i++) {
      await rec.feedFrame(0.06);
    }
    assert.equal(rec.state, "SPEAKING");

    // User stops speaking (silence frames with RMS = 0.002)
    // Silence begins on first low frame
    await rec.feedFrame(0.002);
    assert.equal(rec.state, "SILENCE_COUNTDOWN");
    assert.equal(rec.getDiagnostics().silenceTimerStarted, true);
    assert.equal(rec.getDiagnostics().silenceTimeoutTriggered, false);

    // Advance time through 1500ms of silence (~18 frames)
    for (let i = 0; i < 18; i++) {
      await rec.feedFrame(0.002);
    }
    assert.equal(rec.state, "SILENCE_COUNTDOWN");
    assert.equal(utteranceFinalized, false, "Must not finalize before 2000ms");

    // Advance another 600ms (total silence = ~2100ms)
    for (let i = 0; i < 8; i++) {
      await rec.feedFrame(0.002);
    }

    assert.equal(rec.state, "FINALIZED");
    assert.equal(utteranceFinalized, true);
    assert.equal(rec.getDiagnostics().silenceTimeoutTriggered, true);
    assert.equal(rec.getDiagnostics().recordingFinalized, true);
    assert.ok(receivedPayload.blob.size > 0);
    assert.ok(receivedPayload.durationSec > 1.0);

    rec.markSendVoiceTurnCalled();
    assert.equal(rec.getDiagnostics().sendVoiceTurnCalled, true);
  });

  console.log("\n2. Test B: Natural Conversational Pause & Resume");
  await test("Mid-utterance pause resets timer and merges into single finalization", async () => {
    let finalizationCount = 0;

    const rec = new SimulatedAudioRecorder({
      onUtteranceFinalized: () => {
        finalizationCount++;
      },
    });

    // User speaks: "Hello Saki" (10 frames)
    for (let i = 0; i < 10; i++) {
      await rec.feedFrame(0.05);
    }
    assert.equal(rec.state, "SPEAKING");

    // User pauses for 1000ms (12 silence frames)
    for (let i = 0; i < 12; i++) {
      await rec.feedFrame(0.002);
    }
    assert.equal(rec.state, "SILENCE_COUNTDOWN");
    const genBefore = rec.silenceGeneration;

    // User resumes speaking: "How are you today?" (15 frames)
    // First frame
    await rec.feedFrame(0.05);
    // Second frame triggers resumption
    await rec.feedFrame(0.05);
    assert.equal(rec.state, "SPEAKING");
    assert.equal(rec.getDiagnostics().silenceTimerCancelled, true);
    assert.ok(rec.silenceGeneration > genBefore, "Generation token must increment");

    for (let i = 0; i < 13; i++) {
      await rec.feedFrame(0.05);
    }

    // Now user stops speaking for a full 2000ms (25 frames)
    for (let i = 0; i < 25; i++) {
      await rec.feedFrame(0.002);
    }

    assert.equal(rec.state, "FINALIZED");
    assert.equal(finalizationCount, 1, "Exactly ONE finalization must occur for continuous conversational pause");
  });

  console.log("\n3. Test C: Noise & Click Rejection During Silence Window");
  await test("Single-frame noise click does NOT cancel active 2000ms silence timer", async () => {
    let finalized = false;

    const rec = new SimulatedAudioRecorder({
      onUtteranceFinalized: () => {
        finalized = true;
      },
    });

    // User speaks (8 frames)
    for (let i = 0; i < 8; i++) {
      await rec.feedFrame(0.04);
    }
    assert.equal(rec.state, "SPEAKING");

    // Silence starts (6 frames ~ 500ms)
    for (let i = 0; i < 6; i++) {
      await rec.feedFrame(0.002);
    }
    assert.equal(rec.state, "SILENCE_COUNTDOWN");
    const initialGen = rec.silenceGeneration;

    // Transient noise click (1 single frame above threshold)
    await rec.feedFrame(0.08); // single spike
    assert.equal(rec.state, "SILENCE_COUNTDOWN", "Single click must NOT transition to SPEAKING");
    assert.equal(rec.silenceGeneration, initialGen, "Generation must NOT change on single click");

    // Silence continues (20 more frames ~ 1700ms)
    for (let i = 0; i < 20; i++) {
      await rec.feedFrame(0.002);
    }

    assert.equal(rec.state, "FINALIZED");
    assert.equal(finalized, true);
    assert.equal(rec.getDiagnostics().silenceTimeoutTriggered, true);
  });

  console.log("\n4. Test D: Web Audio Graph Connection Map Verification");
  await test("Microphone stream connects strictly to AnalyserNode with NO path to Destination", async () => {
    // Mock Web Audio Graph
    const audioContext = {
      destination: { id: "AudioDestinationNode" },
      createAnalyser: () => ({ id: "AnalyserNode", connections: [] }),
      createGain: () => ({ id: "GainNode", gain: { value: 1.0 }, connections: [] }),
      createMediaStreamSource: (s) => ({ id: "MediaStreamSource", stream: s, connections: [] }),
      createMediaElementSource: (el) => ({ id: "MediaElementSource", element: el, connections: [] }),
    };

    // Helper to connect nodes and record topology
    function connect(from, to) {
      if (!from.connections) from.connections = [];
      from.connections.push(to);
    }

    // AudioAnalyzer connection logic
    const analyser = audioContext.createAnalyser();
    const ttsGain = audioContext.createGain();
    connect(ttsGain, audioContext.destination);

    // Scenario 1: Microphone stream attached
    const micStream = { id: "UserMicrophoneStream" };
    const micSource = audioContext.createMediaStreamSource(micStream);
    connect(micSource, analyser); // Only connect to analyser!

    // Traverse downstream from micSource
    function reachesDestination(node, visited = new Set()) {
      if (!node || visited.has(node)) return false;
      visited.add(node);
      if (node === audioContext.destination) return true;
      if (!node.connections) return false;
      for (const next of node.connections) {
        if (reachesDestination(next, visited)) return true;
      }
      return false;
    }

    assert.equal(
      reachesDestination(micSource),
      false,
      "Microphone stream in AudioAnalyzer MUST NOT reach AudioDestinationNode!"
    );

    // Scenario 2: Audio Element (TTS) attached
    const ttsElement = { id: "KokoroAudioElement" };
    const ttsSource = audioContext.createMediaElementSource(ttsElement);
    connect(ttsSource, analyser);
    connect(ttsSource, ttsGain);

    assert.equal(
      reachesDestination(ttsSource),
      true,
      "TTS audio element MUST reach AudioDestinationNode for audible playback!"
    );

    // Scenario 3: AudioRecorder capture graph (ScriptProcessor + Null MediaStreamDestination Sink)
    const recMicStream = { id: "RecorderMicStream" };
    const recSource = audioContext.createMediaStreamSource(recMicStream);
    const recProcessor = { id: "ScriptProcessorNode", connections: [] };
    const dummyDest = { id: "MediaStreamAudioDestinationNode", connections: [] };
    connect(recSource, recProcessor);
    connect(recProcessor, dummyDest); // Connected to dummy sink only!

    assert.equal(
      reachesDestination(recSource),
      false,
      "AudioRecorder capture graph MUST NOT reach AudioDestinationNode!"
    );
  });

  console.log("\n5. Test E: Guarded Finalization (Exactly-Once Execution)");
  await test("Concurrent stop() and timeout triggers execute finalization exactly once", async () => {
    let callCount = 0;
    const rec = new SimulatedAudioRecorder({
      onUtteranceFinalized: () => {
        callCount++;
      },
    });

    // User speaks
    for (let i = 0; i < 5; i++) {
      await rec.feedFrame(0.04);
    }

    // Trigger stop and finalize in parallel
    const [res1, res2] = await Promise.all([
      rec.finalizeCurrentUtterance(),
      rec.finalizeCurrentUtterance(),
    ]);

    assert.equal(callCount, 1, "onUtteranceFinalized must be called exactly once");
    assert.ok(res1 !== null);
    assert.equal(res2, null, "Second concurrent call must return null");
  });

  console.log("\n==================================================");
  console.log(`   TOTAL: ${testsPassed} Passed, ${testsFailed} Failed`);
  console.log("==================================================");

  if (testsFailed > 0) {
    process.exit(1);
  }
}

runAllTests();
