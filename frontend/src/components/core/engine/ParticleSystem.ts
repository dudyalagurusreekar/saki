/**
 * 3D Particle System Engine (Sprint 3)
 * Simulates specialized state-driven particle dynamics:
 * - Serene low-activity orbit for IDLE
 * - Receptive expansion envelope for LISTENING
 * - Inward convergence for PROCESSING
 * - Multi-frequency neural swirl for THINKING
 * - Directional radar sweep for SEARCHING
 * - Optical focal contraction for VISION
 * - Logarithmic inward vortex for REMEMBERING
 * - Directional kinetic thrust vectors for ACTING
 * - Vocal harmonic expansion waves for SPEAKING
 * - Restrained warning pulse for ERROR
 */

import { Particle, StateVisualProfile, Vector3D, Point2D, QualityConfig, AudioMetrics } from "../types";
import { rgbaToString } from "./StateTransitionManager";

export function project3D(
  pos: Vector3D,
  centerX: number,
  centerY: number,
  cameraDistance: number = 600
): Point2D {
  const zOffset = pos.z + cameraDistance;
  const scale = zOffset > 1 ? cameraDistance / zOffset : 1;
  return {
    x: centerX + pos.x * scale,
    y: centerY + pos.y * scale,
    scale,
    alpha: Math.min(1.0, Math.max(0.1, (pos.z + 400) / 800)),
    depth: pos.z,
  };
}

export class ParticleSystem {
  private particles: Particle[] = [];
  private baseRadius: number = 100;
  private cameraDistance: number = 600;
  private timeAccumulator: number = 0;
  private radarAngle: number = 0;

  constructor(baseRadius: number, count: number = 180) {
    this.baseRadius = baseRadius;
    this.initParticles(count);
  }

  public initParticles(count: number): void {
    this.particles = [];
    for (let i = 0; i < count; i++) {
      this.particles.push(this.createParticle(i, count));
    }
  }

  public setParticleCount(targetCount: number): void {
    if (this.particles.length === targetCount) return;
    if (this.particles.length < targetCount) {
      const diff = targetCount - this.particles.length;
      for (let i = 0; i < diff; i++) {
        this.particles.push(this.createParticle(this.particles.length, targetCount));
      }
    } else {
      this.particles.length = targetCount;
    }
  }

  private createParticle(id: number, total: number): Particle {
    const layer = id % 5 === 0 
      ? "inner" 
      : id % 5 === 4 
      ? "outer_cloud" 
      : id % 10 === 0 
      ? "probe" 
      : "orbital";

    let radiusMultiplier = 1.0;
    if (layer === "inner") radiusMultiplier = 0.55 + Math.random() * 0.45;
    else if (layer === "orbital") radiusMultiplier = 1.1 + Math.random() * 1.35;
    else if (layer === "outer_cloud") radiusMultiplier = 2.1 + Math.random() * 1.8;
    else if (layer === "probe") radiusMultiplier = 1.0 + Math.random() * 2.8;

    const angle = (id / total) * Math.PI * 2 + (Math.random() - 0.5) * 0.5;
    const inclination = (Math.random() - 0.5) * Math.PI * 0.8;
    const radius = this.baseRadius * radiusMultiplier;

    const x = radius * Math.cos(angle) * Math.cos(inclination);
    const y = radius * Math.sin(angle) * Math.cos(inclination) * 0.55;
    const z = radius * Math.sin(inclination);

    const baseSize = layer === "inner" ? 1.5 + Math.random() * 1.5 : 1.2 + Math.random() * 2.6;

    return {
      id,
      pos: { x, y, z },
      originPos: { x, y, z },
      vel: {
        x: (Math.random() - 0.5) * 0.3,
        y: (Math.random() - 0.5) * 0.3,
        z: (Math.random() - 0.5) * 0.3,
      },
      size: baseSize,
      baseSize,
      color: { r: 255, g: 255, b: 255, a: 0.8 },
      alpha: 0.3 + Math.random() * 0.7,
      life: Math.random() * 100,
      maxLife: 80 + Math.random() * 100,
      orbitRadius: radius,
      orbitAngle: angle,
      orbitSpeed: (0.003 + Math.random() * 0.007) * (id % 2 === 0 ? 1 : -0.8),
      orbitInclination: inclination,
      turbulenceSeed: Math.random() * 1000,
      layer,
      pulseOffset: Math.random() * Math.PI * 2,
      vectorHeading: Math.random() * Math.PI * 2,
    };
  }

  public update(
    deltaTime: number,
    profile: StateVisualProfile,
    reducedMotion: boolean,
    audioMetrics?: AudioMetrics
  ): void {
    if (reducedMotion) return;

    const isAudioActive = audioMetrics?.isAudioActive ?? false;
    const audioSpeedBoost = isAudioActive && audioMetrics ? 1.0 + audioMetrics.speechActivity * 0.8 : 1.0;

    this.timeAccumulator += deltaTime * 0.001 * profile.rotationSpeedMultiplier * audioSpeedBoost;
    this.radarAngle += 0.0025 * profile.particleSpeedMultiplier * deltaTime;

    const speedMult = profile.particleSpeedMultiplier * 0.06 * deltaTime * audioSpeedBoost;
    const turbulence = profile.particleTurbulence + (isAudioActive && audioMetrics ? audioMetrics.midBand * 0.4 : 0.0);
    const swarmRadius = profile.particleSwarmRadius;
    const flowMode = profile.particleFlowMode;

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      // Update particle lifecycle
      p.life += deltaTime * 0.05;
      if (p.life > p.maxLife) {
        p.life = 0;
        p.alpha = 0.3 + Math.random() * 0.7;
      }

      // Orbital angle advancement with multi-layered speed
      const layerSpeedMult = p.layer === "inner" ? 1.4 : p.layer === "probe" ? 2.0 : 1.0;
      p.orbitAngle += p.orbitSpeed * speedMult * layerSpeedMult;

      const t = this.timeAccumulator + p.turbulenceSeed;
      let targetRadius = p.orbitRadius * swarmRadius;

      // -------------------------------------------------------------
      // Specialized Flow Dynamics per State Behavior
      // -------------------------------------------------------------
      if (isAudioActive && audioMetrics) {
        // REAL-TIME AUDIO VOICE REACTIVITY: Acoustic expansion wave + treble sibilance flare
        const vocalAcousticWave =
          audioMetrics.smoothedVolume * 0.28 +
          Math.sin(t * 5 + p.id * 0.25) * (14 * audioMetrics.midBand);
        const sibilanceFlare = p.layer === "outer_cloud" ? audioMetrics.highBand * 0.22 : 0.0;

        targetRadius = p.orbitRadius * (1.0 + vocalAcousticWave + sibilanceFlare);
        p.pos.y += Math.sin(t * 4 + p.pulseOffset) * (0.8 + audioMetrics.midBand) * speedMult;
      } else {
        switch (flowMode) {
          case "receptive_expand": {
            // LISTENING: Outer particles expand subtly into a receptive acoustic envelope
            targetRadius = p.orbitRadius * (1.15 + Math.sin(t * 2 + p.id) * 0.1);
            p.pos.y += Math.sin(t * 1.5 + p.pulseOffset) * 0.4 * speedMult;
            break;
          }

          case "converging_prep": {
            // PROCESSING: Controlled energy increase, streams inward
            p.orbitRadius = Math.max(this.baseRadius * 0.42, p.orbitRadius - 0.3 * speedMult);
            if (p.orbitRadius <= this.baseRadius * 0.48) {
              p.orbitRadius = this.baseRadius * (1.7 + Math.random() * 1.1);
            }
            break;
          }

          case "neural_swirl": {
            // THINKING: Pronounced layered orbital swirl & internal circulation
            const swirlShift = Math.sin(t * 3.5 + p.pulseOffset) * 14 * turbulence;
            p.pos.z += Math.cos(t * 2.8 + p.pulseOffset) * 10 * turbulence;
            p.pos.y += swirlShift * 0.4;
            break;
          }

          case "search_radar": {
            // SEARCHING: Directional radar sweep beams & probe ray divergence
            const angleDiff = (p.orbitAngle - this.radarAngle) % (Math.PI * 2);
            if (Math.abs(angleDiff) < 0.6 || Math.abs(angleDiff - Math.PI * 2) < 0.6) {
              targetRadius = p.orbitRadius * 1.4; // Flare along radar beam
            }
            if (p.layer === "probe") {
              p.orbitRadius += 0.45 * speedMult;
              if (p.orbitRadius > this.baseRadius * 4.0) {
                p.orbitRadius = this.baseRadius * (0.6 + Math.random() * 0.4);
              }
            }
            break;
          }

          case "optical_scan": {
            // VISION: Contract toward focal optical plane, emphasizing outer scanning rings
            targetRadius = p.orbitRadius * 0.92;
            p.pos.z *= 0.95; // Flatten along focal lens plane
            break;
          }

          case "inward_recall": {
            // REMEMBERING: Subtle inward memory recall vortex
            p.orbitRadius = Math.max(this.baseRadius * 0.5, p.orbitRadius - 0.15 * speedMult);
            if (p.orbitRadius <= this.baseRadius * 0.52) {
              p.orbitRadius = this.baseRadius * (1.8 + Math.random() * 0.8);
            }
            break;
          }

          case "kinetic_vector": {
            // ACTING: Directional tangential kinetic vector thrusts
            p.pos.x += Math.cos(p.vectorHeading || 0) * 0.8 * speedMult;
            p.pos.y += Math.sin(p.vectorHeading || 0) * 0.4 * speedMult;
            if (Math.abs(p.pos.x) > this.baseRadius * 3.2 || Math.abs(p.pos.y) > this.baseRadius * 2.2) {
              p.pos.x = (Math.random() - 0.5) * this.baseRadius;
              p.pos.y = (Math.random() - 0.5) * this.baseRadius;
            }
            break;
          }

          case "speech_harmonic_pulse": {
            // SPEAKING (Fallback simulated): Smooth rhythmic vocal cadence expansions
            const vocalPulse = Math.sin(t * 6 + p.id * 0.2) * 12 * profile.speechHarmonicDepth;
            targetRadius = p.orbitRadius * (1.0 + vocalPulse / this.baseRadius);
            p.pos.y += Math.sin(t * 4 + p.pulseOffset) * 0.6 * speedMult;
            break;
          }

          case "restrained_caution": {
            // ERROR: Restrained warning jitter (controlled & non-alarming)
            p.pos.x += (Math.random() - 0.5) * 1.5 * turbulence;
            p.pos.y += (Math.random() - 0.5) * 1.2 * turbulence;
            break;
          }

          case "orbital":
          default: {
            // IDLE: Serene, slow gentle orbital drift
            p.pos.y += Math.sin(t * 0.8 + p.pulseOffset) * 0.2 * speedMult;
            break;
          }
        }
      }

      // 3D Orbital Coordinate recalculation
      const cosAngle = Math.cos(p.orbitAngle);
      const sinAngle = Math.sin(p.orbitAngle);
      const cosInc = Math.cos(p.orbitInclination + Math.sin(t * 0.4) * 0.12 * profile.ringTiltMultiplier);
      const sinInc = Math.sin(p.orbitInclination);

      const targetX = targetRadius * cosAngle * cosInc;
      const targetY = targetRadius * sinAngle * cosInc * 0.55 + Math.sin(t * 2 + p.pulseOffset) * 6 * turbulence;
      const targetZ = targetRadius * sinInc + Math.cos(t * 1.4 + p.pulseOffset) * 10 * turbulence;

      // Smooth interpolation toward target coordinates
      p.pos.x += (targetX - p.pos.x) * 0.12;
      p.pos.y += (targetY - p.pos.y) * 0.12;
      p.pos.z += (targetZ - p.pos.z) * 0.12;
    }
  }

  /**
   * Renders particles filtered by depth (front vs back of core)
   */
  public renderLayer(
    ctx: CanvasRenderingContext2D,
    centerX: number,
    centerY: number,
    profile: StateVisualProfile,
    glowIntensity: number,
    layerType: "back" | "front",
    qualityConfig: QualityConfig,
    audioMetrics?: AudioMetrics
  ): void {
    ctx.save();
    ctx.globalCompositeOperation = "lighter";

    const isAudioActive = audioMetrics?.isAudioActive ?? false;
    const dynamicGlow = glowIntensity * (1.0 + (isAudioActive && audioMetrics ? audioMetrics.midBand * 0.3 : 0.0));

    // Project and filter particles by z-depth and active density factor
    const projected: Array<{ p: Particle; pt: Point2D }> = [];
    const activeCount = Math.floor(this.particles.length * Math.max(0.3, profile.particleDensityFactor));

    for (let i = 0; i < activeCount; i++) {
      const p = this.particles[i];
      const isFront = p.pos.z >= 0;
      if ((layerType === "front" && isFront) || (layerType === "back" && !isFront)) {
        const pt = project3D(p.pos, centerX, centerY, this.cameraDistance);
        projected.push({ p, pt });
      }
    }

    // -------------------------------------------------------------
    // Constellation Interconnect Lines (for THINKING, VISION, REMEMBERING)
    // -------------------------------------------------------------
    if (profile.constellationLines && qualityConfig.maxConstellationLines > 0 && layerType === "front") {
      let lineCount = 0;
      const maxLines = qualityConfig.maxConstellationLines;
      const thresholdDist = 68;

      ctx.lineWidth = 0.8;
      for (let i = 0; i < projected.length; i++) {
        if (lineCount >= maxLines) break;
        for (let j = i + 1; j < projected.length; j++) {
          if (lineCount >= maxLines) break;
          const p1 = projected[i].pt;
          const p2 = projected[j].pt;
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < thresholdDist) {
            const lineAlpha = (1 - dist / thresholdDist) * 0.4 * profile.hudAlpha;
            ctx.strokeStyle = rgbaToString(profile.secondaryColor, lineAlpha);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
            lineCount++;
          }
        }
      }
    }

    // -------------------------------------------------------------
    // Particle Rendering
    // -------------------------------------------------------------
    for (let i = 0; i < projected.length; i++) {
      const { p, pt } = projected[i];
      const audioParticleScale = isAudioActive && audioMetrics ? 1.0 + audioMetrics.highBand * 0.4 : 1.0;
      const renderSize = Math.max(
        0.6,
        p.baseSize * pt.scale * (0.8 + Math.sin(p.pulseOffset) * 0.2) * audioParticleScale
      );
      const particleAlpha = Math.min(1.0, Math.max(0.05, p.alpha * pt.alpha * dynamicGlow));

      // Mix palette based on particle layer
      const color = p.id % 4 === 0 
        ? profile.accentColor 
        : p.id % 2 === 0 
        ? profile.secondaryColor 
        : profile.primaryColor;

      ctx.fillStyle = rgbaToString(color, particleAlpha);
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, renderSize, 0, Math.PI * 2);
      ctx.fill();

      // Bright focal center for larger particles in front layer
      if (renderSize > 1.8 && layerType === "front") {
        const whiteAlpha = Math.min(1.0, particleAlpha * (0.9 + (isAudioActive && audioMetrics ? audioMetrics.highBand * 0.3 : 0.0)));
        ctx.fillStyle = `rgba(255, 255, 255, ${whiteAlpha})`;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, renderSize * 0.38, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.restore();
  }
}

