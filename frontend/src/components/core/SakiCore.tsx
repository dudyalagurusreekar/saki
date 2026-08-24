"use client";

/**
 * SakiCore Component
 * Reusable GPU-accelerated visualization engine for Saki AI.
 * Renders glowing central spherical energy, 3D orbital rings, irregular particle swarms,
 * and futuristic HUD telemetry driven by real SakiState events.
 */

import React, { useSyncExternalStore } from "react";
import { SakiCoreProps } from "./types";
import { useSakiCore } from "./hooks/useSakiCore";

function subscribeReducedMotion(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  mediaQuery.addEventListener("change", callback);
  return () => mediaQuery.removeEventListener("change", callback);
}

function getReducedMotionSnapshot() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function getReducedMotionServerSnapshot() {
  return false;
}

export default function SakiCore({
  state = "IDLE",
  activity,
  theme = "night_sky",
  quality = "auto",
  opacity = 1.0,
  scale = 1.0,
  reducedMotion = false,
  className = "",
  showHudTelemetry = true,
  audioSensitivity = 1.0,
  onFpsUpdate,
}: SakiCoreProps) {
  const prefersReducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotionSnapshot,
    getReducedMotionServerSnapshot
  );

  const effectiveReducedMotion = reducedMotion || prefersReducedMotion;

  const { canvasRef, fps } = useSakiCore({
    state,
    activity,
    theme,
    quality,
    opacity,
    scale,
    reducedMotion: effectiveReducedMotion,
    showHudTelemetry,
    audioSensitivity,
    onFpsUpdate,
  });

  return (
    <div 
      className={`relative w-full h-full flex items-center justify-center overflow-hidden pointer-events-none ${className}`}
      data-saki-state={state}
      data-fps={fps}
      aria-label={`Saki Core Visual Engine - State: ${state}`}
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full block touch-none"
        style={{
          opacity,
          willChange: "transform, opacity",
          transform: "translateZ(0)", // Force GPU layer promotion
        }}
      />
    </div>
  );
}
