import React from "react";
import SkyEnvironment from "./environment/SkyEnvironment";
import { SakiTheme } from "../lib/theme";

export interface SkyBackgroundProps {
  theme?: SakiTheme;
  reducedMotion?: boolean;
  cloudDensity?: "low" | "medium" | "high";
  className?: string;
}

/**
 * SkyBackground Component
 * Drop-in backward-compatible wrapper around Sprint 13 SkyEnvironment.
 */
export default function SkyBackground({
  theme = "night_sky",
  reducedMotion = false,
  cloudDensity = "medium",
  className = "",
}: SkyBackgroundProps) {
  return (
    <SkyEnvironment
      theme={theme}
      reducedMotion={reducedMotion}
      cloudDensity={cloudDensity}
      className={className}
    />
  );
}
