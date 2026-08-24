/**
 * Saki Core Master Renderer (Sprint 10)
 * Coordinates the multi-layered 3D canvas pipeline, Web Audio real-time reactivity,
 * delta-time animation loop, DPR scaling, quality management, and performance monitoring.
 */

import { SakiState } from "../../../lib/api";
import { QualityLevel, QualityConfig, StateVisualProfile, AudioMetrics } from "../types";
import { QUALITY_CONFIGS } from "../config/coreConfig";
import { StateTransitionManager, rgbaToString } from "./StateTransitionManager";
import { EnergySphere } from "./EnergySphere";
import { ParticleSystem } from "./ParticleSystem";
import { OrbitalRings } from "./OrbitalRings";
import { HudGeometry } from "./HudGeometry";
import { AudioAnalyzer, createDefaultAudioMetrics } from "./AudioAnalyzer";
import { sakiVoicePlayer } from "./SakiVoicePlayer";

export interface RendererOptions {
  quality: QualityLevel;
  glowIntensity: number;
  reducedMotion: boolean;
  theme: "clear_sky" | "night_sky";
  scale: number;
  opacity: number;
  showHudTelemetry: boolean;
  audioSensitivity?: number;
  audioAnalyzer?: AudioAnalyzer;
  onFpsUpdate?: (fps: number) => void;
}

export class CoreRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private options: RendererOptions;

  private stateManager: StateTransitionManager;
  private energySphere: EnergySphere;
  private particleSystem: ParticleSystem;
  private orbitalRings: OrbitalRings;
  private hudGeometry: HudGeometry;
  private audioAnalyzer: AudioAnalyzer | null = null;

  private isRunning: boolean = false;
  private animFrameId: number | null = null;
  private lastTime: number = 0;
  private baseRadius: number = 75;

  private width: number = 0;
  private height: number = 0;
  private dpr: number = 1;

  // Performance telemetry
  private frameCount: number = 0;
  private lastFpsCheck: number = 0;
  private currentFps: number = 60;
  private activityText: string = "";
  private lastAudioMetrics: AudioMetrics = createDefaultAudioMetrics();

  constructor(canvas: HTMLCanvasElement, initialOptions: Partial<RendererOptions> = {}) {
    this.canvas = canvas;
    const context = canvas.getContext("2d", { alpha: true });
    if (!context) {
      throw new Error("Could not initialize 2D Canvas context for SakiCore.");
    }
    this.ctx = context;

    this.options = {
      quality: initialOptions.quality ?? "auto",
      glowIntensity: initialOptions.glowIntensity ?? 1.0,
      reducedMotion: initialOptions.reducedMotion ?? false,
      theme: initialOptions.theme ?? "night_sky",
      scale: initialOptions.scale ?? 1.0,
      opacity: initialOptions.opacity ?? 1.0,
      showHudTelemetry: initialOptions.showHudTelemetry ?? true,
      audioSensitivity: initialOptions.audioSensitivity ?? 1.0,
      audioAnalyzer: initialOptions.audioAnalyzer,
      onFpsUpdate: initialOptions.onFpsUpdate,
    };

    this.audioAnalyzer = initialOptions.audioAnalyzer || sakiVoicePlayer.getAnalyzer();

    const qualityConfig = this.getQualityConfig();

    this.stateManager = new StateTransitionManager("IDLE");
    this.energySphere = new EnergySphere();
    this.particleSystem = new ParticleSystem(this.baseRadius, qualityConfig.particleCount);
    this.orbitalRings = new OrbitalRings(this.baseRadius);
    this.hudGeometry = new HudGeometry();

    this.handleResize();
  }

  public getQualityConfig(): QualityConfig {
    return QUALITY_CONFIGS[this.options.quality] || QUALITY_CONFIGS.auto;
  }

  public setAudioAnalyzer(analyzer: AudioAnalyzer | null): void {
    this.audioAnalyzer = analyzer;
  }

  public getAudioMetrics(): AudioMetrics {
    return this.lastAudioMetrics;
  }

  public setState(state: SakiState, activity?: string): void {
    this.stateManager.setState(state);
    if (activity !== undefined) {
      this.activityText = activity;
    }
  }

  public updateOptions(newOptions: Partial<RendererOptions>): void {
    const prevQuality = this.options.quality;
    this.options = { ...this.options, ...newOptions };

    if (newOptions.audioAnalyzer !== undefined) {
      this.audioAnalyzer = newOptions.audioAnalyzer;
    }

    if (newOptions.audioSensitivity !== undefined && this.audioAnalyzer) {
      this.audioAnalyzer.updateConfig({ sensitivity: newOptions.audioSensitivity });
    }

    if (newOptions.quality && newOptions.quality !== prevQuality) {
      const config = this.getQualityConfig();
      this.particleSystem.setParticleCount(config.particleCount);
    }
  }

  public resize(width: number, height: number): void {
    this.width = width;
    this.height = height;

    const qualityConfig = this.getQualityConfig();
    const rawDpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    this.dpr = Math.min(rawDpr, qualityConfig.dprLimit);

    this.canvas.width = Math.floor(width * this.dpr);
    this.canvas.height = Math.floor(height * this.dpr);
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;

    // Recompute base core radius based on smaller viewport dimension
    const minDim = Math.min(width, height);
    this.baseRadius = Math.max(40, Math.min(130, minDim * 0.16 * this.options.scale));

    this.particleSystem = new ParticleSystem(this.baseRadius, qualityConfig.particleCount);
    this.orbitalRings.setBaseRadius(this.baseRadius);
  }

  public handleResize(): void {
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      this.resize(rect.width, rect.height);
    }
  }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.lastTime = performance.now();
    this.lastFpsCheck = this.lastTime;
    this.frameCount = 0;
    if (this.audioAnalyzer) {
      this.audioAnalyzer.resume();
    }
    this.loop(this.lastTime);
  }

  public stop(): void {
    this.isRunning = false;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.audioAnalyzer) {
      this.audioAnalyzer.suspend();
    }
  }

  public destroy(): void {
    this.stop();
  }

  private loop = (now: number): void => {
    if (!this.isRunning) return;

    // Delta time normalization (capped at 100ms to prevent huge jumps after suspension)
    const rawDelta = now - this.lastTime;
    const deltaTime = Math.min(100, Math.max(1, rawDelta));
    this.lastTime = now;

    // FPS Telemetry calculation
    this.frameCount++;
    if (now - this.lastFpsCheck >= 1000) {
      this.currentFps = Math.round((this.frameCount * 1000) / (now - this.lastFpsCheck));
      this.frameCount = 0;
      this.lastFpsCheck = now;
      this.options.onFpsUpdate?.(this.currentFps);

      // Auto-quality safeguard
      if (this.options.quality === "auto" && this.currentFps < 35) {
        this.particleSystem.setParticleCount(QUALITY_CONFIGS.medium.particleCount);
      }
    }

    // Extract real-time Web Audio metrics (fast, zero React re-renders)
    const audioMetrics = this.audioAnalyzer
      ? this.audioAnalyzer.getMetrics()
      : sakiVoicePlayer.getMetrics();
    this.lastAudioMetrics = audioMetrics;

    // Step physics & interpolation
    const profile = this.stateManager.update(now);
    const reduced = this.options.reducedMotion;

    this.energySphere.update(deltaTime, profile, reduced, audioMetrics);
    this.particleSystem.update(deltaTime, profile, reduced, audioMetrics);
    this.orbitalRings.update(deltaTime, profile, reduced, audioMetrics);
    this.hudGeometry.update(deltaTime, profile, reduced, audioMetrics);

    // Render multi-pass composite frame
    this.renderFrame(profile, audioMetrics);

    this.animFrameId = requestAnimationFrame(this.loop);
  };

  private renderFrame(profile: StateVisualProfile, audioMetrics: AudioMetrics): void {
    const ctx = this.ctx;
    const w = this.width * this.dpr;
    const h = this.height * this.dpr;

    if (w <= 0 || h <= 0) return;

    ctx.save();
    ctx.scale(this.dpr, this.dpr);

    const centerX = this.width * 0.5;
    const centerY = this.height * 0.5;
    const qualityConfig = this.getQualityConfig();
    const glow = this.options.glowIntensity;

    // Set overall container opacity
    ctx.globalAlpha = this.options.opacity;

    // -------------------------------------------------------------
    // PASS 0: Clear Canvas & Ambient Backdrop
    // -------------------------------------------------------------
    ctx.clearRect(0, 0, this.width, this.height);

    // Subtle dark cosmic radial gradient backdrop
    const bgRadius = Math.max(this.width, this.height) * 0.65;
    const bgGrad = ctx.createRadialGradient(centerX, centerY, this.baseRadius * 0.5, centerX, centerY, bgRadius);
    const isNight = this.options.theme === "night_sky";

    if (isNight) {
      bgGrad.addColorStop(0, rgbaToString(profile.ambientBackdrop, 0.45));
      bgGrad.addColorStop(0.55, rgbaToString(profile.ambientBackdrop, 0.15));
      bgGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
    } else {
      // Clear sky ambient aura
      bgGrad.addColorStop(0, rgbaToString(profile.primaryColor, 0.18));
      bgGrad.addColorStop(0.5, rgbaToString(profile.secondaryColor, 0.08));
      bgGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
    }

    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, this.width, this.height);

    // -------------------------------------------------------------
    // PASS 1: Back Depth Layer (Behind Core)
    // -------------------------------------------------------------
    this.orbitalRings.renderLayer(ctx, centerX, centerY, profile, glow, "back", qualityConfig.ringCount, audioMetrics);
    this.particleSystem.renderLayer(ctx, centerX, centerY, profile, glow, "back", qualityConfig, audioMetrics);

    // -------------------------------------------------------------
    // PASS 2: Central Luminous Energy Sphere
    // -------------------------------------------------------------
    this.energySphere.render(
      ctx,
      centerX,
      centerY,
      this.baseRadius,
      profile,
      glow,
      this.options.reducedMotion,
      audioMetrics
    );

    // -------------------------------------------------------------
    // PASS 3: Front Depth Layer (In Front of Core)
    // -------------------------------------------------------------
    this.particleSystem.renderLayer(ctx, centerX, centerY, profile, glow, "front", qualityConfig, audioMetrics);
    this.orbitalRings.renderLayer(ctx, centerX, centerY, profile, glow, "front", qualityConfig.ringCount, audioMetrics);

    // -------------------------------------------------------------
    // PASS 4: Sci-Fi HUD Geometry & Peripheral Indicators
    // -------------------------------------------------------------
    this.hudGeometry.render(
      ctx,
      centerX,
      centerY,
      this.baseRadius,
      profile,
      this.activityText,
      this.options.showHudTelemetry,
      audioMetrics
    );

    ctx.restore();
  }
}

