/**
 * 3D Orbital Rings Engine
 * Renders multiple gyroscopic and elliptical orbital rings with true 3D projection,
 * front/back depth splitting for volumetric occlusion, segmented dashes, and satellite nodes.
 */

import { OrbitalRingDefinition, StateVisualProfile, Vector3D, Point2D, AudioMetrics } from "../types";
import { createDefaultOrbitalRings } from "../config/coreConfig";
import { project3D } from "./ParticleSystem";
import { rgbaToString } from "./StateTransitionManager";

export class OrbitalRings {
  private rings: OrbitalRingDefinition[] = [];
  private baseRadius: number = 100;
  private cameraDistance: number = 600;

  constructor(baseRadius: number) {
    this.baseRadius = baseRadius;
    this.rings = createDefaultOrbitalRings(baseRadius);
  }

  public setBaseRadius(radius: number): void {
    if (this.baseRadius === radius) return;
    this.baseRadius = radius;
    this.rings = createDefaultOrbitalRings(radius);
  }

  public update(
    deltaTime: number,
    profile: StateVisualProfile,
    reducedMotion: boolean,
    audioMetrics?: AudioMetrics
  ): void {
    if (reducedMotion) return;

    const isAudioActive = audioMetrics?.isAudioActive ?? false;
    const audioSpeedBoost = isAudioActive && audioMetrics ? 1.0 + audioMetrics.midBand * 0.6 : 1.0;
    const speedMult = profile.rotationSpeedMultiplier * 0.06 * deltaTime * audioSpeedBoost;

    for (let i = 0; i < this.rings.length; i++) {
      const ring = this.rings[i];
      ring.currentAngle += ring.rotationSpeed * speedMult;

      // Update orbiting satellite nodes
      for (let j = 0; j < ring.nodes.length; j++) {
        const node = ring.nodes[j];
        node.angle += node.speed * speedMult;
        node.pulsePhase += (0.05 + (isAudioActive && audioMetrics ? audioMetrics.midBand * 0.08 : 0.0)) * speedMult;
      }
    }
  }

  /**
   * Transforms a 2D ring coordinate with 3D Euler tilt angles and rotation
   */
  private transformRingPoint(
    angle: number,
    ring: OrbitalRingDefinition,
    profile: StateVisualProfile,
    audioMetrics?: AudioMetrics
  ): Vector3D {
    const isAudioActive = audioMetrics?.isAudioActive ?? false;
    const audioExpansion = isAudioActive && audioMetrics ? audioMetrics.smoothedVolume * 0.10 : 0.0;
    const scaleFactor =
      (ring.radius > this.baseRadius * 1.4
        ? profile.outerStructureScale
        : 1.0 + (profile.outerStructureScale - 1.0) * 0.4) + audioExpansion;

    const r = ring.radius * ring.asymmetryFactor * scaleFactor;
    // Base 2D point in ring coordinate plane
    const baseRot = angle + ring.currentAngle;
    const x = r * Math.cos(baseRot);
    const y = 0;
    const z = r * Math.sin(baseRot);

    // Apply Dynamic Tilt X with bass resonance
    const audioTiltBoost = isAudioActive && audioMetrics ? audioMetrics.lowBand * 0.25 : 0.0;
    const effectiveTiltMultiplier = profile.ringTiltMultiplier + audioTiltBoost;

    const tiltX = ring.tiltX * effectiveTiltMultiplier;
    const cosX = Math.cos(tiltX);
    const sinX = Math.sin(tiltX);
    const y1 = y * cosX - z * sinX;
    const z1 = y * sinX + z * cosX;

    // Apply Tilt Y
    const tiltY = ring.tiltY * effectiveTiltMultiplier;
    const cosY = Math.cos(tiltY);
    const sinY = Math.sin(tiltY);
    const x2 = x * cosY + z1 * sinY;
    const z2 = -x * sinY + z1 * cosY;

    // Apply Tilt Z
    const tiltZ = ring.tiltZ;
    const cosZ = Math.cos(tiltZ);
    const sinZ = Math.sin(tiltZ);
    const x3 = x2 * cosZ - y1 * sinZ;
    const y3 = x2 * sinZ + y1 * cosZ;

    return { x: x3, y: y3, z: z2 };
  }

  /**
   * Renders rings with depth sorting (back vs front arcs)
   */
  public renderLayer(
    ctx: CanvasRenderingContext2D,
    centerX: number,
    centerY: number,
    profile: StateVisualProfile,
    glowIntensity: number,
    layerType: "back" | "front",
    ringLimit: number = 6,
    audioMetrics?: AudioMetrics
  ): void {
    ctx.save();
    ctx.globalCompositeOperation = "lighter";

    const isAudioActive = audioMetrics?.isAudioActive ?? false;
    const dynamicGlow = glowIntensity * (1.0 + (isAudioActive && audioMetrics ? audioMetrics.midBand * 0.35 : 0.0));
    const ringsToRender = this.rings.slice(0, ringLimit);
    const steps = 64; // Polyline curve approximation

    for (let rIdx = 0; rIdx < ringsToRender.length; rIdx++) {
      const ring = ringsToRender[rIdx];
      const ringColor = rIdx % 2 === 0 ? profile.secondaryColor : profile.primaryColor;

      // -----------------------------------------------------------
      // Generate 3D samples around the perimeter
      // -----------------------------------------------------------
      const pts3D: Vector3D[] = [];
      const pts2D: Point2D[] = [];

      for (let s = 0; s <= steps; s++) {
        const theta = (s / steps) * Math.PI * 2;
        const p3 = this.transformRingPoint(theta, ring, profile, audioMetrics);
        pts3D.push(p3);
        pts2D.push(project3D(p3, centerX, centerY, this.cameraDistance));
      }

      // -----------------------------------------------------------
      // Draw segmented arc strokes matching the requested depth layer
      // -----------------------------------------------------------
      ctx.lineWidth = ring.lineWidth + (isAudioActive && audioMetrics && rIdx === 0 ? audioMetrics.lowBand * 0.8 : 0.0);
      ctx.setLineDash(ring.dashArray);

      for (let s = 0; s < steps; s++) {
        const pA3 = pts3D[s];
        const pB3 = pts3D[s + 1];
        const pA2 = pts2D[s];
        const pB2 = pts2D[s + 1];

        const isFront = (pA3.z + pB3.z) / 2 >= 0;
        if ((layerType === "front" && isFront) || (layerType === "back" && !isFront)) {
          const depthAlpha = isFront ? 0.75 : 0.28;
          ctx.strokeStyle = rgbaToString(ringColor, depthAlpha * dynamicGlow);

          ctx.beginPath();
          ctx.moveTo(pA2.x, pA2.y);
          ctx.lineTo(pB2.x, pB2.y);
          ctx.stroke();
        }
      }

      // -----------------------------------------------------------
      // Draw Azimuth / Degree Tick Marks (shimmer with High-Band)
      // -----------------------------------------------------------
      if (ring.showTicks && ring.tickCount > 0) {
        ctx.setLineDash([]);
        ctx.lineWidth = 1.0;
        const tickStep = (Math.PI * 2) / ring.tickCount;
        const audioTickShimmer = isAudioActive && audioMetrics ? audioMetrics.highBand * 0.4 : 0.0;

        for (let t = 0; t < ring.tickCount; t++) {
          const theta = t * tickStep;
          const p3 = this.transformRingPoint(theta, ring, profile, audioMetrics);
          const isFront = p3.z >= 0;

          if ((layerType === "front" && isFront) || (layerType === "back" && !isFront)) {
            const p2 = project3D(p3, centerX, centerY, this.cameraDistance);
            const tickLength = (t % 4 === 0 ? 6 : 3) * p2.scale * (1.0 + (isAudioActive && audioMetrics ? audioMetrics.highBand * 0.5 : 0.0));
            const alpha = Math.min(1.0, (isFront ? 0.6 : 0.2) * dynamicGlow + audioTickShimmer);

            ctx.strokeStyle = rgbaToString(profile.accentColor, alpha);
            ctx.beginPath();
            ctx.moveTo(p2.x, p2.y - tickLength * 0.5);
            ctx.lineTo(p2.x, p2.y + tickLength * 0.5);
            ctx.stroke();
          }
        }
      }

      // -----------------------------------------------------------
      // Draw Orbiting Satellite Nodes (pulse with Mid-Band)
      // -----------------------------------------------------------
      if (ring.hasNodes) {
        ctx.setLineDash([]);
        for (let n = 0; n < ring.nodes.length; n++) {
          const node = ring.nodes[n];
          const node3 = this.transformRingPoint(node.angle, ring, profile, audioMetrics);
          const isFront = node3.z >= 0;

          if ((layerType === "front" && isFront) || (layerType === "back" && !isFront)) {
            const node2 = project3D(node3, centerX, centerY, this.cameraDistance);
            const audioNodeBoost = isAudioActive && audioMetrics ? 1.0 + audioMetrics.midBand * 0.6 : 1.0;
            const nodeSize = node.size * node2.scale * (1 + Math.sin(node.pulsePhase) * 0.25) * audioNodeBoost;
            const nodeAlpha = Math.min(1.0, (isFront ? 0.95 : 0.4) * dynamicGlow);

            // Outer node flare
            ctx.fillStyle = rgbaToString(profile.accentColor, nodeAlpha);
            ctx.beginPath();
            ctx.arc(node2.x, node2.y, nodeSize * 1.6, 0, Math.PI * 2);
            ctx.fill();

            // Inner white bright core
            ctx.fillStyle = `rgba(255, 255, 255, ${nodeAlpha})`;
            ctx.beginPath();
            ctx.arc(node2.x, node2.y, nodeSize * 0.7, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    }

    ctx.restore();
  }
}

