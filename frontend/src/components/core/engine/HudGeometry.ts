import { StateVisualProfile, AudioMetrics } from "../types";
import { rgbaToString } from "./StateTransitionManager";

export class HudGeometry {
  private reticleAngle: number = 0;
  private radarSweepAngle: number = 0;
  private fluxValue: number = 98.4;
  private fluxPhase: number = 0;

  public update(
    deltaTime: number,
    profile: StateVisualProfile,
    reducedMotion: boolean,
    audioMetrics?: AudioMetrics
  ): void {
    if (!reducedMotion) {
      const isAudioActive = audioMetrics?.isAudioActive ?? false;
      const audioSpeedMult = isAudioActive && audioMetrics ? 1.0 + audioMetrics.speechActivity * 0.5 : 1.0;

      this.reticleAngle += 0.0004 * profile.rotationSpeedMultiplier * deltaTime * audioSpeedMult;
      this.radarSweepAngle += 0.003 * profile.particleSpeedMultiplier * deltaTime;
      this.fluxPhase += 0.002 * profile.corePulsingSpeed * deltaTime;
      this.fluxValue = 97.0 + Math.sin(this.fluxPhase) * 2.8 + Math.cos(this.fluxPhase * 2.1) * 0.9;
    }
  }

  public render(
    ctx: CanvasRenderingContext2D,
    centerX: number,
    centerY: number,
    baseRadius: number,
    profile: StateVisualProfile,
    activityText?: string,
    showTelemetry: boolean = true,
    audioMetrics?: AudioMetrics
  ): void {
    const isAudioActive = audioMetrics?.isAudioActive ?? false;
    const alpha = profile.hudAlpha * (1.0 + (isAudioActive && audioMetrics ? audioMetrics.speechActivity * 0.15 : 0.0));
    if (alpha <= 0.05) return;

    ctx.save();
    ctx.globalCompositeOperation = "source-over";

    const primaryColor = profile.primaryColor;
    const accentColor = profile.accentColor;
    const coreR = baseRadius * profile.coreRadiusMultiplier;
    const outerScale = profile.outerStructureScale + (isAudioActive && audioMetrics ? audioMetrics.smoothedVolume * 0.08 : 0.0);

    // -------------------------------------------------------------
    // 1. SEARCHING: Directional Radar Sweep Beam (Only in search mode)
    // -------------------------------------------------------------
    if (profile.particleFlowMode === "search_radar") {
      const sweepLen = baseRadius * 2.8 * outerScale;
      const beamX = centerX + Math.cos(this.radarSweepAngle) * sweepLen;
      const beamY = centerY + Math.sin(this.radarSweepAngle) * sweepLen;

      ctx.strokeStyle = rgbaToString(accentColor, 0.5 * alpha);
      ctx.lineWidth = 1.2;
      ctx.setLineDash([8, 4]);
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(beamX, beamY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // -------------------------------------------------------------
    // 3. Quadrant Corner Brackets (Framing the Core)
    // -------------------------------------------------------------
    const frameSize = baseRadius * 2.3 * outerScale;
    const bracketLen = 14;
    ctx.strokeStyle = rgbaToString(accentColor, 0.4 * alpha);
    ctx.lineWidth = 1.2;

    // Top-Left
    ctx.beginPath();
    ctx.moveTo(centerX - frameSize, centerY - frameSize + bracketLen);
    ctx.lineTo(centerX - frameSize, centerY - frameSize);
    ctx.lineTo(centerX - frameSize + bracketLen, centerY - frameSize);
    ctx.stroke();

    // Top-Right
    ctx.beginPath();
    ctx.moveTo(centerX + frameSize - bracketLen, centerY - frameSize);
    ctx.lineTo(centerX + frameSize, centerY - frameSize);
    ctx.lineTo(centerX + frameSize, centerY - frameSize + bracketLen);
    ctx.stroke();

    // Bottom-Left
    ctx.beginPath();
    ctx.moveTo(centerX - frameSize, centerY + frameSize - bracketLen);
    ctx.lineTo(centerX - frameSize, centerY + frameSize);
    ctx.lineTo(centerX - frameSize + bracketLen, centerY + frameSize);
    ctx.stroke();

    // Bottom-Right
    ctx.beginPath();
    ctx.moveTo(centerX + frameSize - bracketLen, centerY + frameSize);
    ctx.lineTo(centerX + frameSize, centerY + frameSize);
    ctx.lineTo(centerX + frameSize, centerY + frameSize - bracketLen);
    ctx.stroke();

    // -------------------------------------------------------------
    // 4. Sci-Fi Peripheral Telemetry & State Readouts
    // -------------------------------------------------------------
    if (showTelemetry) {
      ctx.font = "9px 'Geist Mono', 'Courier New', monospace";

      // Top-Left Label: System Identifier
      ctx.fillStyle = rgbaToString(accentColor, 0.7 * alpha);
      ctx.fillText("SYS // SAKI_CORE_v2.0", centerX - frameSize + 4, centerY - frameSize - 6);

      // Top-Right Label: Flux Level / Audio Activity
      const fluxText = isAudioActive && audioMetrics
        ? `VOICE: ${(audioMetrics.smoothedVolume * 100).toFixed(0)}%`
        : `FLUX: ${this.fluxValue.toFixed(1)}%`;
      const fluxMetrics = ctx.measureText(fluxText);
      ctx.fillStyle = rgbaToString(primaryColor, 0.7 * alpha);
      ctx.fillText(fluxText, centerX + frameSize - fluxMetrics.width - 4, centerY - frameSize - 6);

      // Bottom-Right Coordinate Hash
      const hashText = `ORBIT_RAD: ${(coreR * 2).toFixed(0)}PX`;
      const hashMetrics = ctx.measureText(hashText);
      ctx.fillStyle = rgbaToString(primaryColor, 0.5 * alpha);
      ctx.fillText(hashText, centerX + frameSize - hashMetrics.width - 4, centerY + frameSize + 16);
    }

    ctx.restore();
  }
}

