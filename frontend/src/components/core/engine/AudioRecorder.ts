/**
 * Saki Browser Audio Recorder & Intelligent VAD Engine
 * Captures microphone audio via Web Audio API, provides local Voice Activity Detection (VAD)
 * with 2.0-second silence auto-submission, debounce noise rejection, live countdowns,
 * and encodes raw PCM directly into standard 16kHz 16-bit mono WAV format for Saki's local brain.
 */

export const DEFAULT_SILENCE_TIMEOUT_MS = 2000;
export const DEFAULT_SPEECH_THRESHOLD = 0.015;
export const DEFAULT_MIN_SPEECH_FRAMES = 2; // ~170ms sustained frames to reject clicks/spikes

export type VADState =
  | "IDLE"
  | "SPEAKING"
  | "SILENCE_DETECTED"
  | "SILENCE_COUNTDOWN"
  | "FINALIZING"
  | "FINALIZED";

export interface VADDiagnostics {
  turnId: string;
  state: VADState;
  speechDetected: boolean;
  speechStartedAt: number | null;
  silenceStartedAt: number | null;
  silenceElapsedMs: number;
  silenceTimerStarted: boolean;
  silenceTimerCancelled: boolean;
  silenceTimeoutTriggered: boolean;
  recordingStarted: boolean;
  recordingStopped: boolean;
  recordingFinalized: boolean;
  audioDurationMs: number;
  audioBlobSize: number;
  sendVoiceTurnCalled: boolean;
  silenceGeneration: number;
}

export interface AudioRecorderOptions {
  sampleRate?: number;
  silenceTimeoutMs?: number;      // Default: 2000ms (2.0s silence window)
  speechThreshold?: number;       // RMS amplitude threshold (Default: 0.015)
  enableAutoSubmit?: boolean;     // Enable natural end-of-speech auto-submission
  onVolumeChange?: (volume: number) => void;
  onSpeechStart?: () => void;
  onSpeechResumed?: () => void;
  onSilenceStart?: () => void;
  onSilenceCountdown?: (remainingSec: number, fraction: number) => void;
  onUtteranceFinalized?: (payload: { blob: Blob; base64: string; durationSec: number }) => void;
  onError?: (error: Error) => void;
}

function getMonotonicNow(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

export class AudioRecorder {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private muteGainNode: GainNode | null = null;
  private dummyDestinationNode: AudioNode | null = null;
  private pcmChunks: Float32Array[] = [];
  private totalSamples: number = 0;
  private isRecording: boolean = false;
  private isFinalizing: boolean = false;
  private options: AudioRecorderOptions;
  private sampleRate: number = 16000;

  // VAD state tracking
  private state: VADState = "IDLE";
  private consecutiveSpeechFrames: number = 0;
  private hasSpokenInUtterance: boolean = false;
  private silenceStartTimestamp: number | null = null;
  private silenceFinalizeTimer: ReturnType<typeof setTimeout> | null = null;
  private silenceGeneration: number = 0;
  private turnId: string;

  // Diagnostics tracking
  private diagnostics: VADDiagnostics;

  constructor(options: AudioRecorderOptions = {}) {
    this.options = {
      silenceTimeoutMs: DEFAULT_SILENCE_TIMEOUT_MS,
      speechThreshold: DEFAULT_SPEECH_THRESHOLD,
      enableAutoSubmit: true,
      ...options,
    };
    this.turnId = `turn-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    this.diagnostics = this.createDefaultDiagnostics();
  }

  private createDefaultDiagnostics(): VADDiagnostics {
    return {
      turnId: this.turnId,
      state: "IDLE",
      speechDetected: false,
      speechStartedAt: null,
      silenceStartedAt: null,
      silenceElapsedMs: 0,
      silenceTimerStarted: false,
      silenceTimerCancelled: false,
      silenceTimeoutTriggered: false,
      recordingStarted: false,
      recordingStopped: false,
      recordingFinalized: false,
      audioDurationMs: 0,
      audioBlobSize: 0,
      sendVoiceTurnCalled: false,
      silenceGeneration: 0,
    };
  }

  public getDiagnostics(): VADDiagnostics {
    return { ...this.diagnostics };
  }

  public markSendVoiceTurnCalled(): void {
    this.diagnostics.sendVoiceTurnCalled = true;
  }

  public getIsRecording(): boolean {
    return this.isRecording;
  }

  public getIsSpeaking(): boolean {
    return this.state === "SPEAKING";
  }

  public getState(): VADState {
    return this.state;
  }

  /**
   * Requests microphone access and begins listening with active VAD.
   */
  public async start(): Promise<boolean> {
    if (this.isRecording) return true;

    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      const err = new Error("Microphone capture (getUserMedia) is not supported in this browser.");
      this.options.onError?.(err);
      throw err;
    }

    try {
      this.pcmChunks = [];
      this.totalSamples = 0;
      this.consecutiveSpeechFrames = 0;
      this.hasSpokenInUtterance = false;
      this.state = "IDLE";
      this.silenceStartTimestamp = null;
      this.isFinalizing = false;
      this.silenceGeneration = 0;
      this.turnId = `turn-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      this.diagnostics = this.createDefaultDiagnostics();
      this.diagnostics.recordingStarted = true;
      this.clearSilenceTimers();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.mediaStream = stream;

      // Connect microphone stream directly to Core AudioAnalyzer strictly for visual metrics during LISTENING
      try {
        const { SakiVoicePlayer } = await import("./SakiVoicePlayer");
        SakiVoicePlayer.getInstance().getAnalyzer().connectMediaStream(stream);
      } catch (e) {
        console.warn("[AudioRecorder] Could not connect stream to AudioAnalyzer:", e);
      }

      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) {
        throw new Error("Web Audio API is not supported in this browser.");
      }

      const ctx = new AudioCtx();
      this.audioContext = ctx;
      this.sampleRate = ctx.sampleRate;

      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      const source = ctx.createMediaStreamSource(stream);
      // 4096 buffer size at 48kHz ~ 85ms per frame; at 16kHz ~ 256ms per frame
      const processor = ctx.createScriptProcessor(4096, 1, 1);

      // Create a zero-gain mute node
      const muteGain = ctx.createGain();
      muteGain.gain.value = 0.0;

      processor.onaudioprocess = (e: AudioProcessingEvent) => {
        // Zero output buffer to guarantee 0 audio leak to destination
        const outputBuffer = e.outputBuffer;
        for (let c = 0; c < outputBuffer.numberOfChannels; c++) {
          outputBuffer.getChannelData(c).fill(0);
        }

        if (!this.isRecording || this.isFinalizing) return;
        const inputData = e.inputBuffer.getChannelData(0);

        // Store PCM frame for output WAV encoding
        const copy = new Float32Array(inputData);
        this.pcmChunks.push(copy);
        this.totalSamples += copy.length;

        // 1. Calculate RMS volume & normalized level
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        const normalizedVol = Math.min(1.0, Math.max(0.0, rms * 5.0));
        this.options.onVolumeChange?.(normalizedVol);

        // 2. Intelligent VAD & Natural End-of-Speech Management
        this.processVADFrame(rms);
      };

      // Safest supported silent-output technique:
      // Connect processor to an in-memory MediaStreamDestination (null sink)
      // or to an unrouted gain node. NEVER connect to ctx.destination!
      let dummySink: AudioNode | null = null;
      if (typeof ctx.createMediaStreamDestination === "function") {
        dummySink = ctx.createMediaStreamDestination();
        source.connect(processor);
        processor.connect(dummySink);
      } else {
        source.connect(processor);
        processor.connect(muteGain);
        // Note: muteGain is deliberately NEVER connected to ctx.destination
      }

      this.sourceNode = source;
      this.scriptProcessor = processor;
      this.muteGainNode = muteGain;
      this.dummyDestinationNode = dummySink;
      this.isRecording = true;

      console.log(`[VAD Diagnostics] Microphone capture started (turnId=${this.turnId}, sampleRate=${this.sampleRate})`);
      return true;
    } catch (err: unknown) {
      this.cleanup();
      const errorObj = err instanceof Error ? err : new Error(String(err));
      this.options.onError?.(errorObj);
      throw errorObj;
    }
  }

  /**
   * Evaluates each audio frame against VAD thresholds and manages natural end-of-speech auto-finalization.
   */
  public processVADFrame(rms: number): void {
    const threshold = this.options.speechThreshold ?? DEFAULT_SPEECH_THRESHOLD;
    const silenceTimeout = this.options.silenceTimeoutMs ?? DEFAULT_SILENCE_TIMEOUT_MS;
    const now = getMonotonicNow();

    if (rms >= threshold) {
      // Speech frame detected
      this.consecutiveSpeechFrames++;

      if (this.consecutiveSpeechFrames >= DEFAULT_MIN_SPEECH_FRAMES) {
        if (this.state !== "SPEAKING") {
          if (this.state === "SILENCE_COUNTDOWN" || this.silenceStartTimestamp !== null) {
            // User resumed speaking: invalidate pending silence timer
            this.silenceGeneration++;
            this.clearSilenceTimers();
            this.state = "SPEAKING";
            this.diagnostics.state = "SPEAKING";
            this.diagnostics.silenceTimerCancelled = true;
            this.diagnostics.silenceGeneration = this.silenceGeneration;
            console.log(`[VAD Diagnostics] Speech resumed — silence timer cancelled (gen=${this.silenceGeneration}, turnId=${this.turnId})`);
            this.options.onSpeechResumed?.();
          } else {
            // Initial speech onset
            this.hasSpokenInUtterance = true;
            this.state = "SPEAKING";
            this.diagnostics.state = "SPEAKING";
            this.diagnostics.speechDetected = true;
            this.diagnostics.speechStartedAt = now;
            this.clearSilenceTimers();
            console.log(`[VAD Diagnostics] Speech onset detected (turnId=${this.turnId}, rms=${rms.toFixed(4)})`);
            this.options.onSpeechStart?.();
          }
        }
      }
    } else {
      // Low energy / silence frame: Reset consecutive speech frame counter
      // This prevents single noise spikes during silence from falsely resuming speech
      this.consecutiveSpeechFrames = 0;

      if (this.hasSpokenInUtterance) {
        if (this.state === "SPEAKING") {
          // Transition from SPEAKING to SILENCE_COUNTDOWN
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

          console.log(`[VAD Diagnostics] Silence detected. Starting ${silenceTimeout}ms timer (gen=${currentGen}, turnId=${this.turnId})`);
          this.options.onSilenceStart?.();

          if (this.options.enableAutoSubmit) {
            this.startSilenceFinalization(silenceTimeout, currentGen);
          }
        } else if (this.state === "SILENCE_COUNTDOWN" && this.silenceStartTimestamp !== null) {
          // Update live silence countdown metrics
          const elapsed = now - this.silenceStartTimestamp;
          this.diagnostics.silenceElapsedMs = elapsed;
          const total = this.options.silenceTimeoutMs ?? DEFAULT_SILENCE_TIMEOUT_MS;
          const remainingSec = Math.max(0, (silenceTimeout - elapsed) / 1000);
          const fraction = Math.min(1.0, elapsed / total);
          this.options.onSilenceCountdown?.(remainingSec, fraction);
        }
      }
    }
  }

  /**
   * Schedules natural conversational finalization after speech ends using a generation-tagged timer.
   */
  private startSilenceFinalization(timeoutMs: number, generation: number): void {
    if (this.silenceFinalizeTimer !== null) {
      clearTimeout(this.silenceFinalizeTimer);
      this.silenceFinalizeTimer = null;
    }

    this.silenceFinalizeTimer = setTimeout(async () => {
      const now = getMonotonicNow();
      const elapsed = this.silenceStartTimestamp !== null ? now - this.silenceStartTimestamp : 0;

      // Validate generation token, state, and recording status to prevent stale timer race conditions
      if (
        this.isRecording &&
        !this.isFinalizing &&
        this.state === "SILENCE_COUNTDOWN" &&
        this.silenceGeneration === generation &&
        this.hasSpokenInUtterance &&
        elapsed >= timeoutMs - 50 // 50ms tolerance for clock jitter
      ) {
        this.diagnostics.silenceTimeoutTriggered = true;
        this.diagnostics.silenceElapsedMs = elapsed;
        console.log(`[VAD Diagnostics] ${timeoutMs}ms silence timer fired (elapsed=${Math.round(elapsed)}ms, gen=${generation}). Finalizing utterance...`);
        await this.finalizeCurrentUtterance();
      } else {
        console.log(`[VAD Diagnostics] Stale silence timer discarded (timerGen=${generation}, currentGen=${this.silenceGeneration}, state=${this.state})`);
      }
    }, timeoutMs);
  }

  private clearSilenceTimers(): void {
    if (this.silenceFinalizeTimer !== null) {
      clearTimeout(this.silenceFinalizeTimer);
      this.silenceFinalizeTimer = null;
    }
    this.silenceStartTimestamp = null;
  }

  /**
   * Auto-finalizes the current speech utterance, encodes to 16kHz WAV, and triggers callback.
   * Guarded by `isFinalizing` to guarantee exactly-once execution.
   */
  public async finalizeCurrentUtterance(): Promise<{ blob: Blob; base64: string; durationSec: number } | null> {
    if (this.isFinalizing) return null;
    this.isFinalizing = true;
    this.state = "FINALIZING";
    this.diagnostics.state = "FINALIZING";
    this.clearSilenceTimers();

    try {
      const payload = await this.encodeCurrentAudio();
      this.state = "FINALIZED";
      this.diagnostics.state = "FINALIZED";
      this.diagnostics.recordingFinalized = true;
      this.diagnostics.recordingStopped = true;
      this.diagnostics.audioBlobSize = payload.blob.size;
      this.diagnostics.audioDurationMs = payload.durationSec * 1000;

      // Audio validation: Reject empty or malformed recordings
      if (payload.blob.size === 0 || payload.durationSec < 0.1) {
        console.warn(`[AudioRecorder] Audio validation failed (blobSize=${payload.blob.size}, duration=${payload.durationSec.toFixed(2)}s). Utterance discarded.`);
        this.cleanup();
        return null;
      }

      console.log(`[VAD Diagnostics] Recording finalized successfully: blobSize=${payload.blob.size} bytes, duration=${payload.durationSec.toFixed(2)}s, turnId=${this.turnId}`);
      this.cleanup();
      this.options.onUtteranceFinalized?.(payload);
      return payload;
    } catch (err) {
      this.cleanup();
      console.error("[AudioRecorder] Utterance finalization error:", err);
      return null;
    }
  }

  /**
   * Stops recording and returns standard 16kHz 16-bit mono WAV payload and Base64 string.
   */
  public async stop(): Promise<{ blob: Blob; base64: string; durationSec: number }> {
    if (!this.isRecording) {
      throw new Error("AudioRecorder is not actively recording.");
    }
    this.isFinalizing = true;
    this.state = "FINALIZING";
    this.diagnostics.state = "FINALIZING";
    this.clearSilenceTimers();

    try {
      const payload = await this.encodeCurrentAudio();
      this.state = "FINALIZED";
      this.diagnostics.state = "FINALIZED";
      this.diagnostics.recordingFinalized = true;
      this.diagnostics.recordingStopped = true;
      this.diagnostics.audioBlobSize = payload.blob.size;
      this.diagnostics.audioDurationMs = payload.durationSec * 1000;

      this.cleanup();
      return payload;
    } catch (err) {
      this.cleanup();
      throw err;
    }
  }

  /**
   * Encodes recorded PCM chunks into standard 16kHz mono 16-bit Linear PCM WAV.
   */
  private async encodeCurrentAudio(): Promise<{ blob: Blob; base64: string; durationSec: number }> {
    // 1. Merge all PCM Float32 chunks
    const mergedPcm = new Float32Array(this.totalSamples);
    let offset = 0;
    for (const chunk of this.pcmChunks) {
      mergedPcm.set(chunk, offset);
      offset += chunk.length;
    }

    // 2. Resample to standard 16kHz for Whisper
    const resampledPcm = this.resampleTo16k(mergedPcm, this.sampleRate);
    const durationSec = Math.max(0.1, resampledPcm.length / 16000.0);

    // 3. Encode into standard 16-bit PCM Linear WAV
    const wavArrayBuffer = this.encodeWAV(resampledPcm, 16000);
    const audioBlob = new Blob([wavArrayBuffer], { type: "audio/wav" });
    const base64Data = "data:audio/wav;base64," + this.arrayBufferToBase64(wavArrayBuffer);

    return {
      blob: audioBlob,
      base64: base64Data,
      durationSec,
    };
  }

  /**
   * Linear interpolation resampler to 16kHz.
   */
  private resampleTo16k(audioData: Float32Array, originalRate: number): Float32Array {
    if (originalRate === 16000 || audioData.length === 0) return audioData;
    const targetLength = Math.round((audioData.length * 16000) / originalRate);
    if (targetLength <= 0) return new Float32Array(0);

    const result = new Float32Array(targetLength);
    const ratio = (audioData.length - 1) / Math.max(1, targetLength - 1);

    for (let i = 0; i < targetLength; i++) {
      const pos = i * ratio;
      const index = Math.floor(pos);
      const frac = pos - index;
      if (index + 1 < audioData.length) {
        result[i] = audioData[index] * (1 - frac) + audioData[index + 1] * frac;
      } else {
        result[i] = audioData[index] || 0;
      }
    }
    return result;
  }

  /**
   * Encodes Float32 samples to 16-bit Linear PCM WAV array buffer.
   */
  private encodeWAV(samples: Float32Array, sampleRate: number = 16000): ArrayBuffer {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // RIFF chunk descriptor
    this.writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    this.writeString(view, 8, "WAVE");

    // fmt sub-chunk
    this.writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // Mono channel
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // Byte rate
    view.setUint16(32, 2, true); // Block align
    view.setUint16(34, 16, true); // 16 bits

    // data sub-chunk
    this.writeString(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);

    // 16-bit PCM integer samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return buffer;
  }

  private writeString(view: DataView, offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    let binary = "";
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Releases microphone hardware stream and Web Audio API nodes.
   */
  public cleanup(): void {
    this.isRecording = false;
    this.isFinalizing = false;
    this.clearSilenceTimers();

    try {
      import("./SakiVoicePlayer").then(({ SakiVoicePlayer }) => {
        SakiVoicePlayer.getInstance().getAnalyzer().disconnectSource();
      }).catch(() => {});
    } catch {}

    if (this.scriptProcessor) {
      try {
        this.scriptProcessor.disconnect();
      } catch {}
      this.scriptProcessor = null;
    }

    if (this.muteGainNode) {
      try {
        this.muteGainNode.disconnect();
      } catch {}
      this.muteGainNode = null;
    }

    if (this.dummyDestinationNode) {
      try {
        this.dummyDestinationNode.disconnect();
      } catch {}
      this.dummyDestinationNode = null;
    }

    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {}
      this.sourceNode = null;
    }

    if (this.mediaStream) {
      try {
        this.mediaStream.getTracks().forEach((track) => track.stop());
      } catch {}
      this.mediaStream = null;
    }

    if (this.audioContext && this.audioContext.state !== "closed") {
      try {
        this.audioContext.close();
      } catch {}
      this.audioContext = null;
    }

    this.pcmChunks = [];
    this.totalSamples = 0;
  }
}
