/**
 * Saki Audio Analyzer Engine (Sprint 10)
 * Web Audio API real-time audio analysis extracting normalized amplitude,
 * frequency band energies (low, mid, high), and speech activity confidence
 * with asymmetric attack/decay smoothing and noise-floor gating.
 */

import { AudioMetrics } from "../types";

export type { AudioMetrics };

export interface AudioAnalyzerConfig {
  /** FFT size for AnalyserNode (must be power of 2, e.g. 256, 512, 1024) */
  fftSize: number;
  /** Web Audio built-in smoothing time constant (0.0 - 1.0) */
  smoothingTimeConstant: number;
  /** Fast attack lerp factor for immediate responsiveness to speech onset (0.0 - 1.0) */
  attackLerp: number;
  /** Gradual decay lerp factor for smooth organic settling without abrupt cuts (0.0 - 1.0) */
  decayLerp: number;
  /** Noise floor threshold below which values are gated to 0.0 */
  noiseFloor: number;
  /** Configurable audio sensitivity / gain multiplier */
  sensitivity: number;
  /** Minimum decibels for FFT mapping */
  minDecibels: number;
  /** Maximum decibels for FFT mapping */
  maxDecibels: number;
}

export const DEFAULT_AUDIO_CONFIG: AudioAnalyzerConfig = {
  fftSize: 256,
  smoothingTimeConstant: 0.8,
  attackLerp: 0.35,
  decayLerp: 0.08,
  noiseFloor: 0.02,
  sensitivity: 1.0,
  minDecibels: -90,
  maxDecibels: -10,
};

export function createDefaultAudioMetrics(): AudioMetrics {
  return {
    rawVolume: 0.0,
    smoothedVolume: 0.0,
    lowBand: 0.0,
    midBand: 0.0,
    highBand: 0.0,
    speechActivity: 0.0,
    isAudioActive: false,
    peakFrequency: 0,
    timestamp: typeof performance !== "undefined" ? performance.now() : Date.now(),
  };
}

export class AudioAnalyzer {
  private ctx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private gainNode: GainNode | null = null;
  private sourceNode: AudioNode | null = null;
  private config: AudioAnalyzerConfig;

  private freqData: Uint8Array<ArrayBuffer> | null = null;
  private timeData: Uint8Array<ArrayBuffer> | null = null;

  private currentMetrics: AudioMetrics;
  private isConnected: boolean = false;
  private isDestroyed: boolean = false;

  constructor(customConfig: Partial<AudioAnalyzerConfig> = {}) {
    this.config = { ...DEFAULT_AUDIO_CONFIG, ...customConfig };
    this.currentMetrics = createDefaultAudioMetrics();
  }

  /**
   * Lazily initializes the Web Audio AudioContext and AnalyserNode.
   */
  public ensureContext(): boolean {
    if (this.isDestroyed) return false;
    if (this.ctx && this.analyser) return true;
    if (typeof window === "undefined") return false;

    try {
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextClass) return false;

      const ctx = new AudioContextClass();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = this.config.fftSize;
      analyser.smoothingTimeConstant = this.config.smoothingTimeConstant;
      analyser.minDecibels = this.config.minDecibels;
      analyser.maxDecibels = this.config.maxDecibels;

      const gain = ctx.createGain();
      gain.gain.value = 1.0;

      // DO NOT connect analyser to gain/destination here!
      // AnalyserNode is an analysis sink. Microphone streams connect ONLY to analyser.
      // AudioElements for TTS connect to analyser (for visuals) AND gainNode (for audible output).
      gain.connect(ctx.destination);

      this.ctx = ctx;
      this.analyser = analyser;
      this.gainNode = gain;

      this.freqData = new Uint8Array(analyser.frequencyBinCount) as Uint8Array<ArrayBuffer>;
      this.timeData = new Uint8Array(analyser.fftSize) as Uint8Array<ArrayBuffer>;

      return true;
    } catch (err) {
      console.warn("[AudioAnalyzer] Failed to create AudioContext:", err);
      return false;
    }
  }

  /**
   * Connects an HTMLAudioElement (e.g. Kokoro TTS playback) to the analyzer and speaker graph.
   */
  public connectAudioElement(audioElement: HTMLMediaElement): boolean {
    if (!this.ensureContext() || !this.ctx || !this.analyser || !this.gainNode) return false;

    try {
      // Disconnect prior source if active
      if (this.sourceNode) {
        try {
          this.sourceNode.disconnect();
        } catch {
          // ignore disconnect error on unattached node
        }
      }

      const source = this.ctx.createMediaElementSource(audioElement);
      // Connect to analyser for visualization AND to gainNode for audible speaker playback
      source.connect(this.analyser);
      source.connect(this.gainNode);
      this.sourceNode = source;
      this.isConnected = true;

      // Resume context if suspended
      if (this.ctx.state === "suspended") {
        this.ctx.resume().catch(() => {});
      }

      return true;
    } catch (err) {
      console.warn("[AudioAnalyzer] Failed to connect media element source:", err);
      return false;
    }
  }

  /**
   * Connects a MediaStream (e.g. microphone input) to the analyzer strictly for visual metrics.
   * Microphones are NEVER connected to GainNode or AudioDestinationNode.
   */
  public connectMediaStream(stream: MediaStream): boolean {
    if (!this.ensureContext() || !this.ctx || !this.analyser) return false;

    try {
      if (this.sourceNode) {
        try {
          this.sourceNode.disconnect();
        } catch {
          // ignore
        }
      }

      const source = this.ctx.createMediaStreamSource(stream);
      // Connect ONLY to analyser for visual frequency/energy metrics (NO path to destination/speakers)
      source.connect(this.analyser);
      this.sourceNode = source;
      this.isConnected = true;

      if (this.ctx.state === "suspended") {
        this.ctx.resume().catch(() => {});
      }

      return true;
    } catch (err) {
      console.warn("[AudioAnalyzer] Failed to connect MediaStream source:", err);
      return false;
    }
  }

  /**
   * Connects an arbitrary AudioNode (e.g. AudioBufferSourceNode).
   */
  public connectAudioNode(node: AudioNode): boolean {
    if (!this.ensureContext() || !this.analyser) return false;
    this.disconnectSource();

    try {
      node.connect(this.analyser);
      this.sourceNode = node;
      this.isConnected = true;
      return true;
    } catch (err) {
      console.warn("[AudioAnalyzer] Error connecting AudioNode:", err);
      return false;
    }
  }

  /**
   * Disconnects active audio input node.
   */
  public disconnectSource(): void {
    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {}
      this.sourceNode = null;
    }
    this.isConnected = false;
  }

  /**
   * Computes and returns real-time AudioMetrics with smoothing and normalization.
   */
  public getMetrics(): AudioMetrics {
    const now = typeof performance !== "undefined" ? performance.now() : Date.now();

    if (!this.analyser || !this.isConnected || !this.freqData || !this.timeData) {
      // Gracefully decay existing metrics toward zero
      this.decayMetrics(now);
      return this.currentMetrics;
    }

    try {
      // 1. Fetch frequency domain & time domain bytes
      this.analyser.getByteFrequencyData(this.freqData);
      this.analyser.getByteTimeDomainData(this.timeData);

      // 2. Compute RMS Volume from time-domain waveform
      let sumSquares = 0;
      for (let i = 0; i < this.timeData.length; i++) {
        const normalizedSample = (this.timeData[i] - 128) / 128.0;
        sumSquares += normalizedSample * normalizedSample;
      }
      const rms = Math.sqrt(sumSquares / this.timeData.length);
      const scaledVolume = Math.min(1.0, Math.max(0.0, rms * 2.2 * this.config.sensitivity));
      const rawVolume = scaledVolume > this.config.noiseFloor ? scaledVolume : 0.0;

      // 3. Frequency Band Energy Integration (Peak + Average Blend)
      const sampleRate = this.ctx ? this.ctx.sampleRate : 44100;
      const binCount = this.analyser.frequencyBinCount;
      const hzPerBin = (sampleRate / 2) / binCount;

      let lowMax = 0, lowSum = 0, lowCount = 0;
      let midMax = 0, midSum = 0, midCount = 0;
      let highMax = 0, highSum = 0, highCount = 0;
      let maxVal = 0;
      let peakBin = 0;

      for (let i = 0; i < binCount; i++) {
        const freq = i * hzPerBin;
        const val = this.freqData[i] / 255.0;

        if (val > maxVal) {
          maxVal = val;
          peakBin = i;
        }

        if (freq >= 20 && freq < 250) {
          lowSum += val;
          if (val > lowMax) lowMax = val;
          lowCount++;
        } else if (freq >= 250 && freq < 2000) {
          midSum += val;
          if (val > midMax) midMax = val;
          midCount++;
        } else if (freq >= 2000 && freq <= 8000) {
          highSum += val;
          if (val > highMax) highMax = val;
          highCount++;
        }
      }

      // Blend peak energy in band (65%) with average energy (35%)
      const lowAvg = lowCount > 0 ? lowSum / lowCount : 0.0;
      const midAvg = midCount > 0 ? midSum / midCount : 0.0;
      const highAvg = highCount > 0 ? highSum / highCount : 0.0;

      const targetLow = (lowMax * 0.65 + lowAvg * 0.35) * this.config.sensitivity;
      const targetMid = (midMax * 0.65 + midAvg * 0.35) * this.config.sensitivity;
      const targetHigh = (highMax * 0.65 + highAvg * 0.35) * this.config.sensitivity;

      // Gate noise floor
      const gatedLow = targetLow > this.config.noiseFloor ? Math.min(1.0, targetLow) : 0.0;
      const gatedMid = targetMid > this.config.noiseFloor ? Math.min(1.0, targetMid) : 0.0;
      const gatedHigh = targetHigh > this.config.noiseFloor ? Math.min(1.0, targetHigh) : 0.0;

      // 4. Asymmetric Attack / Decay Exponential Smoothing
      const smoothVol = this.applySmoothing(this.currentMetrics.smoothedVolume, rawVolume);
      const smoothLow = this.applySmoothing(this.currentMetrics.lowBand, gatedLow);
      const smoothMid = this.applySmoothing(this.currentMetrics.midBand, gatedMid);
      const smoothHigh = this.applySmoothing(this.currentMetrics.highBand, gatedHigh);

      // 5. Speech Activity Confidence Calculation
      const speechConfidence = Math.min(
        1.0,
        Math.max(0.0, (smoothMid * 0.55 + smoothVol * 0.35 + smoothHigh * 0.1) * 1.4)
      );
      const isAudioActive = smoothVol > 0.015 || speechConfidence > 0.08;

      this.currentMetrics = {
        rawVolume,
        smoothedVolume: smoothVol,
        lowBand: smoothLow,
        midBand: smoothMid,
        highBand: smoothHigh,
        speechActivity: speechConfidence,
        isAudioActive,
        peakFrequency: Math.round(peakBin * hzPerBin),
        timestamp: now,
      };

      return this.currentMetrics;
    } catch {
      this.decayMetrics(now);
      return this.currentMetrics;
    }
  }

  /**
   * Applies asymmetric attack/decay smoothing: fast rise on speech onset, gradual decay on release.
   */
  private applySmoothing(current: number, target: number): number {
    const factor = target > current ? this.config.attackLerp : this.config.decayLerp;
    const result = current + (target - current) * factor;
    return Math.abs(result) < 0.001 ? 0.0 : Math.min(1.0, Math.max(0.0, result));
  }

  /**
   * Smoothly decays existing metrics toward 0 when audio has stopped.
   */
  private decayMetrics(now: number): void {
    const decay = this.config.decayLerp;
    this.currentMetrics = {
      rawVolume: 0.0,
      smoothedVolume: Math.max(0.0, this.currentMetrics.smoothedVolume * (1 - decay)),
      lowBand: Math.max(0.0, this.currentMetrics.lowBand * (1 - decay)),
      midBand: Math.max(0.0, this.currentMetrics.midBand * (1 - decay)),
      highBand: Math.max(0.0, this.currentMetrics.highBand * (1 - decay)),
      speechActivity: Math.max(0.0, this.currentMetrics.speechActivity * (1 - decay)),
      isAudioActive: this.currentMetrics.smoothedVolume > 0.01,
      peakFrequency: this.currentMetrics.smoothedVolume > 0.01 ? this.currentMetrics.peakFrequency : 0,
      timestamp: now,
    };
  }

  /**
   * Explicitly resets all metrics to baseline zero (e.g. upon barge-in or stop).
   */
  public reset(): void {
    this.currentMetrics = createDefaultAudioMetrics();
  }

  /**
   * Updates analyzer configuration parameters at runtime.
   */
  public updateConfig(newConfig: Partial<AudioAnalyzerConfig>): void {
    this.config = { ...this.config, ...newConfig };
    if (this.analyser) {
      if (newConfig.fftSize) this.analyser.fftSize = newConfig.fftSize;
      if (newConfig.smoothingTimeConstant !== undefined) {
        this.analyser.smoothingTimeConstant = newConfig.smoothingTimeConstant;
      }
      if (newConfig.minDecibels !== undefined) this.analyser.minDecibels = newConfig.minDecibels;
      if (newConfig.maxDecibels !== undefined) this.analyser.maxDecibels = newConfig.maxDecibels;
    }
  }

  /**
   * Pauses the Web Audio context when tab is backgrounded.
   */
  public suspend(): void {
    if (this.ctx && this.ctx.state === "running") {
      this.ctx.suspend().catch(() => {});
    }
  }

  /**
   * Resumes the Web Audio context when tab becomes visible.
   */
  public resume(): void {
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  }

  /**
   * Tears down Web Audio nodes and closes context.
   */
  public destroy(): void {
    this.isDestroyed = true;
    this.disconnectSource();
    if (this.ctx) {
      try {
        this.ctx.close();
      } catch {}
      this.ctx = null;
      this.analyser = null;
      this.gainNode = null;
    }
    this.reset();
  }

  public getContext(): AudioContext | null {
    return this.ctx;
  }

  public getAnalyser(): AnalyserNode | null {
    return this.analyser;
  }
}
