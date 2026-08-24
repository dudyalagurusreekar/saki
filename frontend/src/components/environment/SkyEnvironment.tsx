import React from "react";
import { EnvironmentProps } from "./types";
import Atmosphere from "./Atmosphere";
import SunGlow from "./SunGlow";
import MoonGlow from "./MoonGlow";
import CloudLayer from "./CloudLayer";

/**
 * SkyEnvironment Component (Sprint 13 Master Environment Coordinator)
 * Combines atmospheric gradients, celestial bodies (Sun/Moon), and multi-depth
 * procedural drifting clouds into an immersive, high-performance visual backdrop.
 */
export default function SkyEnvironment({
  theme = "night_sky",
  reducedMotion = false,
  cloudDensity = "medium",
  className = "",
}: EnvironmentProps) {
  const isNight = theme === "night_sky";

  return (
    <div
      className={`fixed inset-0 -z-10 overflow-hidden pointer-events-none ${className}`}
      data-environment-theme={theme}
      aria-hidden="true"
    >
      {/* Layer 1: Atmospheric Background Gradient */}
      <Atmosphere theme={theme} reducedMotion={reducedMotion} />

      {/* Layer 2: Celestial Lighting (Sun or Moon) */}
      {isNight ? (
        <MoonGlow reducedMotion={reducedMotion} />
      ) : (
        <SunGlow reducedMotion={reducedMotion} />
      )}

      {/* Layer 3: Multi-Depth Procedural Drifting Clouds */}
      <CloudLayer
        theme={theme}
        reducedMotion={reducedMotion}
        density={cloudDensity}
      />
    </div>
  );
}
