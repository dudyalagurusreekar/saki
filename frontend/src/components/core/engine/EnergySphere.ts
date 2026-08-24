/**
 * Energy Sphere Engine (Sprint 3)
 * Renders the central pulsating plasma sphere, energetic coronas,
 * internal circulating filaments, harmonic speech respiration, and plasma distortion.
 */

import { StateVisualProfile, AudioMetrics } from "../types";
import { rgbaToString } from "./StateTransitionManager";

export class EnergySphere {
  private pulsePhase: number = 0;
  private speechPhase: number = 0;
  private flareAngles: number[] = [0, 1.25, 2.45, 3.75, 4.95, 0.65];

  public update(
    deltaTime: number,
    profile: StateVisualProfile,
    reducedMotion: boolean,
    audioMetrics?: AudioMetrics
  ): void {
    if (!reducedMotion) {
      const pulseRate = profile.corePulsingSpeed * 0.003 * deltaTime;
      this.pulsePhase += pulseRate;

      // Real audio reactivity vs simulated vocal breathing fallback
      if (audioMetrics?.isAudioActive) {
        // Accelerate internal speech respiration with vocal formants
        this.speechPhase += (0.012 + audioMetrics.midBand * 0.02) * deltaTime;
      } else if (profile.speechHarmonicDepth > 0.05) {
        this.speechPhase += 0.008 * profile.corePulsingSpeed * deltaTime;
      }

      // Rotate internal energy filaments, energized by audio bass & formant bands
      const audioFilamentBoost = audioMetrics?.isAudioActive
        ? 1.0 + audioMetrics.lowBand * 1.5 + audioMetrics.midBand * 0.8
        : 1.0;
      const filamentRate = profile.innerFilamentSpeed * 0.001 * deltaTime * audioFilamentBoost;
      for (let i = 0; i < this.flareAngles.length; i++) {
        this.flareAngles[i] += (0.0006 + i * 0.0003) * filamentRate * profile.rotationSpeedMultiplier;
      }
    }
  }

  public render(
    ctx: CanvasRenderingContext2D,
    centerX: number,
    centerY: number,
    baseRadius: number,
    profile: StateVisualProfile,
    glowIntensity: number,
    reducedMotion: boolean,
    audioMetrics?: AudioMetrics
  ): void {
    ctx.save();
    ctx.translate(centerX, centerY);

    // Compute organic audio expansion vs baseline breathing
    let pulseFactor = 1.0;
    const isAudioActive = audioMetrics?.isAudioActive ?? false;

    if (!reducedMotion) {
      const baseBreathing =
        Math.sin(this.pulsePhase) * 0.05 * profile.coreTurbulence +
        Math.sin(this.pulsePhase * 2.3) * 0.025 * profile.coreTurbulence;

      let speechRespiration = 0;
      if (isAudioActive && audioMetrics) {
        // Real-time audio voice expansion: smooth organic swell (+0% to +35%) + formant flutter
        const audioExpansion = audioMetrics.smoothedVolume * 0.32 + audioMetrics.midBand * 0.15 + (audioMetrics.rawVolume || 0) * 0.08;
        const formantFlutter = Math.sin(this.speechPhase * 3.8) * 0.06 * audioMetrics.midBand;
        const bassResonance = Math.sin(this.pulsePhase * 4.5) * 0.05 * audioMetrics.lowBand;
        speechRespiration = audioExpansion + formantFlutter + bassResonance;
      } else if (profile.speechHarmonicDepth > 0.05) {
        // Fallback simulated breathing
        speechRespiration =
          (Math.sin(this.speechPhase * 3.2) * 0.12 + Math.sin(this.speechPhase * 5.7) * 0.06) *
          profile.speechHarmonicDepth;
      }

      pulseFactor = 1.0 + baseBreathing + speechRespiration;
    } else {
      // Safe subdued pulsation for reduced-motion users
      if (isAudioActive && audioMetrics) {
        pulseFactor = 1.0 + audioMetrics.smoothedVolume * 0.12;
      }
    }

    const coreRadius = Math.max(12, baseRadius * profile.coreRadiusMultiplier * pulseFactor);
    const audioDistortionBoost = isAudioActive && audioMetrics ? audioMetrics.lowBand * 0.45 : 0.0;
    const distortion = Math.min(1.0, profile.energyDistortion + audioDistortionBoost);
    const dynamicGlow = glowIntensity * (1.0 + (isAudioActive && audioMetrics ? audioMetrics.midBand * 0.45 + audioMetrics.smoothedVolume * 0.3 : 0.0));

    // -------------------------------------------------------------
    // PASS 1: Broad Ambient Halo / Corona Glow (Lighter Blend)
    // -------------------------------------------------------------
    ctx.globalCompositeOperation = "lighter";

    const outerGlowRadius = coreRadius * (2.8 + profile.glowIntensityMultiplier * 0.6);
    const outerGrad = ctx.createRadialGradient(0, 0, coreRadius * 0.2, 0, 0, outerGlowRadius);
    outerGrad.addColorStop(0, rgbaToString(profile.primaryColor, 0.42 * dynamicGlow));
    outerGrad.addColorStop(0.35, rgbaToString(profile.secondaryColor, 0.24 * dynamicGlow));
    outerGrad.addColorStop(0.7, rgbaToString(profile.accentColor, 0.09 * dynamicGlow));
    outerGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

    ctx.fillStyle = outerGrad;
    ctx.beginPath();
    ctx.arc(0, 0, outerGlowRadius, 0, Math.PI * 2);
    ctx.fill();

    // -------------------------------------------------------------
    // PASS 2: Mid-Range Plasma Corona & Circulating Energy Filaments
    // -------------------------------------------------------------
    const midGlowRadius = coreRadius * 1.85;
    const midGrad = ctx.createRadialGradient(0, 0, coreRadius * 0.35, 0, 0, midGlowRadius);
    midGrad.addColorStop(0, rgbaToString(profile.accentColor, 0.68 * dynamicGlow));
    midGrad.addColorStop(0.5, rgbaToString(profile.primaryColor, 0.38 * dynamicGlow));
    midGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

    ctx.fillStyle = midGrad;
    ctx.beginPath();
    ctx.arc(0, 0, midGlowRadius, 0, Math.PI * 2);
    ctx.fill();

    // Energetic filament arcs with harmonic distortion
    if (!reducedMotion) {
      ctx.lineWidth = 1.8 + (isAudioActive && audioMetrics ? audioMetrics.highBand * 1.2 : 0.0);
      for (let i = 0; i < this.flareAngles.length; i++) {
        const angle = this.flareAngles[i];
        const arcRadius =
          coreRadius * (1.08 + (i % 3) * 0.16 + Math.sin(this.pulsePhase + i) * 0.08 * distortion);
        const arcSpan = 0.55 + (i % 2) * 0.45 + (isAudioActive && audioMetrics ? audioMetrics.midBand * 0.3 : 0.0);

        ctx.strokeStyle = rgbaToString(
          i % 2 === 0 ? profile.accentColor : profile.secondaryColor,
          (0.35 + (i % 3) * 0.18) * dynamicGlow
        );
        ctx.beginPath();
        ctx.arc(0, 0, arcRadius, angle, angle + arcSpan);
        ctx.stroke();
      }
    }

    // -------------------------------------------------------------
    // PASS 3: Dense Plasma Core with Harmonic Plasma Distortion
    // -------------------------------------------------------------
    const coreGrad = ctx.createRadialGradient(
      -coreRadius * 0.15,
      -coreRadius * 0.15,
      coreRadius * 0.05,
      0,
      0,
      coreRadius
    );
    coreGrad.addColorStop(0, "rgba(255, 255, 255, 0.98)"); // Luminous Hotspot
    coreGrad.addColorStop(0.2, rgbaToString(profile.accentColor, 0.95));
    coreGrad.addColorStop(0.55, rgbaToString(profile.primaryColor, 0.85));
    coreGrad.addColorStop(0.85, rgbaToString(profile.secondaryColor, 0.62));
    coreGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

    ctx.fillStyle = coreGrad;

    // Render warped plasma boundary if distortion > 0
    if (distortion > 0.15 && !reducedMotion) {
      const lobes = 6;
      const steps = 36;
      ctx.beginPath();
      for (let s = 0; s <= steps; s++) {
        const theta = (s / steps) * Math.PI * 2;
        const warp = 1.0 + Math.sin(theta * lobes + this.pulsePhase * 2) * (distortion * 0.08);
        const r = coreRadius * warp;
        const px = Math.cos(theta) * r;
        const py = Math.sin(theta) * r;
        if (s === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fill();
    } else {
      ctx.beginPath();
      ctx.arc(0, 0, coreRadius, 0, Math.PI * 2);
      ctx.fill();
    }

    // -------------------------------------------------------------
    // PASS 4: Inner Core Energy Focal Points & Shimmer
    // -------------------------------------------------------------
    const innerRadius = coreRadius * 0.46;
    const innerGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, innerRadius);
    innerGrad.addColorStop(0, "rgba(255, 255, 255, 1.0)");
    innerGrad.addColorStop(0.5, rgbaToString(profile.accentColor, 0.85));
    innerGrad.addColorStop(1, "rgba(255, 255, 255, 0)");

    ctx.fillStyle = innerGrad;
    ctx.beginPath();
    ctx.arc(0, 0, innerRadius, 0, Math.PI * 2);
    ctx.fill();

    // Concentric boundary energy ring
    ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(0, 0, coreRadius * 0.82, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
  }
}

