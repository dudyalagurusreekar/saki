/**
 * State Transition Manager (Sprint 3)
 * Smoothly interpolates visual parameters, color palettes, speeds, distortion,
 * and specialized particle flow modes between SakiState profiles using ease-in-out cubic easing.
 * Fully interruptible: mid-flight transitions smoothly branch from the current interpolated state.
 */

import { SakiState } from "../../../lib/api";
import { StateVisualProfile, RGBAColor } from "../types";
import { STATE_VISUAL_PROFILES } from "../config/coreConfig";

export function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t;
}

export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function lerpColor(c1: RGBAColor, c2: RGBAColor, t: number): RGBAColor {
  return {
    r: Math.round(lerp(c1.r, c2.r, t)),
    g: Math.round(lerp(c1.g, c2.g, t)),
    b: Math.round(lerp(c1.b, c2.b, t)),
    a: Number(lerp(c1.a, c2.a, t).toFixed(3)),
  };
}

export function rgbaToString(c: RGBAColor, alphaOverride?: number): string {
  const alpha = alphaOverride !== undefined ? alphaOverride : c.a;
  return `rgba(${c.r}, ${c.g}, ${c.b}, ${alpha})`;
}

export class StateTransitionManager {
  private currentProfile: StateVisualProfile;
  private targetProfile: StateVisualProfile;
  private previousProfile: StateVisualProfile;
  
  private transitionProgress: number = 1.0;
  private transitionDuration: number = 550; // ms
  private transitionStartTime: number = 0;
  private isTransitioning: boolean = false;

  constructor(initialState: SakiState = "IDLE") {
    const profile = STATE_VISUAL_PROFILES[initialState] || STATE_VISUAL_PROFILES.IDLE;
    this.currentProfile = { ...profile };
    this.targetProfile = { ...profile };
    this.previousProfile = { ...profile };
  }

  /**
   * Triggers a state transition. If a transition is already in progress,
   * it seamlessly catches the in-flight parameters as the new starting point.
   */
  public setState(newState: SakiState, customDuration?: number): void {
    const target = STATE_VISUAL_PROFILES[newState] || STATE_VISUAL_PROFILES.IDLE;
    if (this.targetProfile.name === newState && !this.isTransitioning) {
      return;
    }

    // Branch from current interpolated state to ensure zero discontinuity
    this.previousProfile = { ...this.currentProfile };
    this.targetProfile = { ...target };
    this.transitionProgress = 0.0;
    this.transitionStartTime = typeof performance !== "undefined" ? performance.now() : Date.now();
    this.transitionDuration = customDuration ?? target.transitionDuration ?? 500;
    this.isTransitioning = true;
  }

  public update(now: number): StateVisualProfile {
    if (!this.isTransitioning) {
      return this.currentProfile;
    }

    const elapsed = now - this.transitionStartTime;
    const rawT = Math.min(1.0, Math.max(0.0, elapsed / Math.max(1, this.transitionDuration)));
    const t = easeInOutCubic(rawT);
    this.transitionProgress = rawT;

    const prev = this.previousProfile;
    const target = this.targetProfile;

    this.currentProfile = {
      name: rawT >= 0.5 ? target.name : prev.name,
      primaryColor: lerpColor(prev.primaryColor, target.primaryColor, t),
      secondaryColor: lerpColor(prev.secondaryColor, target.secondaryColor, t),
      accentColor: lerpColor(prev.accentColor, target.accentColor, t),
      ambientBackdrop: lerpColor(prev.ambientBackdrop, target.ambientBackdrop, t),
      coreRadiusMultiplier: lerp(prev.coreRadiusMultiplier, target.coreRadiusMultiplier, t),
      corePulsingSpeed: lerp(prev.corePulsingSpeed, target.corePulsingSpeed, t),
      coreTurbulence: lerp(prev.coreTurbulence, target.coreTurbulence, t),
      rotationSpeedMultiplier: lerp(prev.rotationSpeedMultiplier, target.rotationSpeedMultiplier, t),
      particleSpeedMultiplier: lerp(prev.particleSpeedMultiplier, target.particleSpeedMultiplier, t),
      particleTurbulence: lerp(prev.particleTurbulence, target.particleTurbulence, t),
      particleSwarmRadius: lerp(prev.particleSwarmRadius, target.particleSwarmRadius, t),
      particleFlowDirection: rawT >= 0.5 ? target.particleFlowDirection : prev.particleFlowDirection,
      particleFlowMode: rawT >= 0.5 ? target.particleFlowMode : prev.particleFlowMode,
      transitionDuration: target.transitionDuration,
      energyDistortion: lerp(prev.energyDistortion, target.energyDistortion, t),
      outerStructureScale: lerp(prev.outerStructureScale, target.outerStructureScale, t),
      innerFilamentSpeed: lerp(prev.innerFilamentSpeed, target.innerFilamentSpeed, t),
      particleDensityFactor: lerp(prev.particleDensityFactor, target.particleDensityFactor, t),
      speechHarmonicDepth: lerp(prev.speechHarmonicDepth, target.speechHarmonicDepth, t),
      ringTiltMultiplier: lerp(prev.ringTiltMultiplier, target.ringTiltMultiplier, t),
      hudAlpha: lerp(prev.hudAlpha, target.hudAlpha, t),
      hudActivityText: rawT >= 0.5 ? target.hudActivityText : prev.hudActivityText,
      glowIntensityMultiplier: lerp(prev.glowIntensityMultiplier, target.glowIntensityMultiplier, t),
      constellationLines: rawT >= 0.5 ? target.constellationLines : prev.constellationLines,
    };

    if (rawT >= 1.0) {
      this.isTransitioning = false;
      this.currentProfile = { ...target };
    }

    return this.currentProfile;
  }

  public getCurrentProfile(): StateVisualProfile {
    return this.currentProfile;
  }

  public getTargetProfile(): StateVisualProfile {
    return this.targetProfile;
  }

  public getProgress(): number {
    return this.transitionProgress;
  }

  public getIsTransitioning(): boolean {
    return this.isTransitioning;
  }
}
