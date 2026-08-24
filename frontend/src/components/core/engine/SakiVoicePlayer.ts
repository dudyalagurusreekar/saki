/**
 * Saki Voice Player Engine (Sprint 10)
 * Browser-side audio playback coordinator connecting Kokoro-82M speech audio
 * to the AudioAnalyzer, managing playback lifecycle, autoplay unlock,
 * and instant barge-in cancellation (< 10ms).
 */

import { AudioAnalyzer, AudioMetrics } from "./AudioAnalyzer";
import { SakiState } from "../../../lib/api";

export type PlaybackStateChangeCallback = (state: SakiState, activity?: string) => void;

export class SakiVoicePlayer {
  private static instance: SakiVoicePlayer | null = null;

  private analyzer: AudioAnalyzer;
  private currentAudio: HTMLAudioElement | null = null;
  private currentBlobUrl: string | null = null;
  private isPlaying: boolean = false;
  private onStateChange: PlaybackStateChangeCallback | null = null;

  private constructor() {
    this.analyzer = new AudioAnalyzer();
  }

  public static getInstance(): SakiVoicePlayer {
    if (!SakiVoicePlayer.instance) {
      SakiVoicePlayer.instance = new SakiVoicePlayer();
    }
    return SakiVoicePlayer.instance;
  }

  public getAnalyzer(): AudioAnalyzer {
    return this.analyzer;
  }

  public getMetrics(): AudioMetrics {
    return this.analyzer.getMetrics();
  }

  public setOnStateChange(cb: PlaybackStateChangeCallback | null): void {
    this.onStateChange = cb;
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }

  /**
   * Plays Saki speech audio from a Blob, Base64 data URL, or standard URL.
   * Connects the audio stream to the AudioAnalyzer so the Core visualizes it in real time.
   */
  public async playSpeech(
    audioSource: Blob | string,
    onComplete?: () => void,
    onError?: (err: unknown) => void
  ): Promise<boolean> {
    // 1. Immediately halt any previously playing utterance
    this.stopPlayback(false);

    if (typeof window === "undefined") return false;

    try {
      // 2. Prepare audio URL
      let url: string;
      if (audioSource instanceof Blob) {
        url = URL.createObjectURL(audioSource);
        this.currentBlobUrl = url;
      } else if (typeof audioSource === "string") {
        url = audioSource;
      } else {
        return false;
      }

      // 3. Create and configure Audio element
      const audio = new Audio();
      audio.crossOrigin = "anonymous";
      audio.src = url;
      audio.preload = "auto";
      this.currentAudio = audio;

      // 4. Connect to Web Audio Analyser
      this.analyzer.connectAudioElement(audio);

      // 5. Setup lifecycle events
      audio.onplay = () => {
        this.isPlaying = true;
        this.onStateChange?.("SPEAKING", "Saki is speaking...");
      };

      audio.onended = () => {
        this.cleanupAudio();
        this.onStateChange?.("IDLE", "");
        onComplete?.();
      };

      audio.onerror = (e) => {
        console.warn("[SakiVoicePlayer] Audio playback error:", e);
        this.cleanupAudio();
        this.onStateChange?.("IDLE", "");
        onError?.(e);
      };

      // 6. Begin playback
      await audio.play();
      return true;
    } catch (err: unknown) {
      console.warn("[SakiVoicePlayer] Failed to initiate speech playback:", err);
      this.cleanupAudio();
      this.onStateChange?.("IDLE", "");
      onError?.(err);
      return false;
    }
  }

  /**
   * Immediately stops active speech playback (< 10ms) and resets analyzer metrics to zero.
   */
  public stopPlayback(notifyBackend: boolean = true): void {
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio.src = "";
      } catch {}
    }

    this.cleanupAudio();
    this.analyzer.reset();

    if (this.isPlaying) {
      this.isPlaying = false;
      this.onStateChange?.("IDLE", "");
    }

    if (notifyBackend && typeof window !== "undefined") {
      // Non-blocking fire-and-forget backend speech cancellation
      fetch("/api/voice/stop", { method: "POST" }).catch(() => {});
    }
  }

  /**
   * Voice barge-in / interruption hook from Sprint 9.
   * Immediately silences playback, flushes audio metrics, and transitions to LISTENING.
   */
  public interruptPlayback(): void {
    this.stopPlayback(true);
    this.onStateChange?.("LISTENING", "User voice detected. Listening...");
  }

  private cleanupAudio(): void {
    this.isPlaying = false;
    if (this.currentBlobUrl) {
      try {
        URL.revokeObjectURL(this.currentBlobUrl);
      } catch {}
      this.currentBlobUrl = null;
    }
    this.analyzer.disconnectSource();
    this.currentAudio = null;
  }

  public destroy(): void {
    this.stopPlayback(false);
    this.analyzer.destroy();
    SakiVoicePlayer.instance = null;
  }
}

export const sakiVoicePlayer = SakiVoicePlayer.getInstance();
