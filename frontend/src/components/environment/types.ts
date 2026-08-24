/**
 * Saki Environment Subsystem Types (Sprint 13)
 * Declarative parameters for procedural cloud layers, celestial bodies,
 * ambient illumination, and atmospheric dynamics.
 */

import { SakiTheme } from "../../lib/theme";

export interface EnvironmentProps {
  theme?: SakiTheme;
  reducedMotion?: boolean;
  cloudDensity?: "low" | "medium" | "high";
  className?: string;
}

export interface CloudDefinition {
  id: string;
  topPercent: number;
  widthPx: number;
  heightPx: number;
  scale: number;
  opacity: number;
  durationSec: number;
  delaySec: number;
  layer: "high_cirrus" | "mid_cumulus" | "low_stratus";
  puffs: Array<{
    topOffsetPx: number;
    leftOffsetPx: number;
    sizePx: number;
    opacity: number;
  }>;
}

export interface AtmosphereProps {
  theme: SakiTheme;
  reducedMotion: boolean;
}

export interface SunGlowProps {
  reducedMotion: boolean;
}

export interface MoonGlowProps {
  reducedMotion: boolean;
}

export interface CloudLayerProps {
  theme: SakiTheme;
  reducedMotion: boolean;
  density?: "low" | "medium" | "high";
}
