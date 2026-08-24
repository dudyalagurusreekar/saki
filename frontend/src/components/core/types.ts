/**
 * Saki Core Engine Type Definitions (Sprint 3)
 * Complete type definitions for 3D projections, particles, orbital geometry,
 * state visual profiles, behavior parameters, and rendering configurations.
 */

import { SakiState } from "../../lib/api";

export type QualityLevel = "auto" | "low" | "medium" | "high" | "ultra";

export type ParticleFlowMode =
  | "orbital"               // Standard circular/elliptical orbit (IDLE baseline)
  | "receptive_expand"      // Outer structure & particles expand subtly to catch user presence (LISTENING)
  | "converging_prep"       // Controlled energy increase streaming inward (PROCESSING)
  | "neural_swirl"          // Multi-frequency layered orbital swirl with internal circulation (THINKING)
  | "search_radar"          // Directional sweep beam & exploratory probe rays (SEARCHING)
  | "optical_scan"          // Focus aperture contraction and lens ring scanning (VISION)
  | "inward_recall"         // Subtle inward vortex and crystalline constellation lines (REMEMBERING)
  | "kinetic_vector"        // Controlled directional tangential thrust jets (ACTING)
  | "speech_harmonic_pulse" // Simulated rhythmic speech respiration & expansion waves (SPEAKING)
  | "restrained_caution";   // Controlled amber-crimson warning pulse with subtle distortion (ERROR)

export interface Vector3D {
  x: number;
  y: number;
  z: number;
}

export interface Point2D {
  x: number;
  y: number;
  scale: number;
  alpha: number;
  depth: number;
}

export interface RGBAColor {
  r: number;
  g: number;
  b: number;
  a: number;
}

export interface Particle {
  id: number;
  pos: Vector3D;
  originPos: Vector3D;
  vel: Vector3D;
  size: number;
  baseSize: number;
  color: RGBAColor;
  alpha: number;
  life: number;
  maxLife: number;
  orbitRadius: number;
  orbitAngle: number;
  orbitSpeed: number;
  orbitInclination: number;
  turbulenceSeed: number;
  layer: "inner" | "orbital" | "outer_cloud" | "probe";
  pulseOffset: number;
  vectorHeading?: number;
}

export interface RingNode {
  angle: number;
  size: number;
  speed: number;
  pulsePhase: number;
}

export interface OrbitalRingDefinition {
  id: string;
  radius: number;
  tiltX: number;
  tiltY: number;
  tiltZ: number;
  rotationSpeed: number;
  currentAngle: number;
  dashArray: number[];
  lineWidth: number;
  color: RGBAColor;
  hasNodes: boolean;
  nodes: RingNode[];
  showTicks: boolean;
  tickCount: number;
  asymmetryFactor: number;
}

export interface StateVisualProfile {
  name: SakiState;
  primaryColor: RGBAColor;         // Main energy sphere & key HUD elements
  secondaryColor: RGBAColor;       // Orbital rings & secondary particles
  accentColor: RGBAColor;          // Flares, bright nodes & reticle accents
  ambientBackdrop: RGBAColor;      // Deep cosmic ambient gradient base
  coreRadiusMultiplier: number;     // Scale multiplier for central energy core (0.8 - 1.6)
  corePulsingSpeed: number;         // Frequency of plasma breathing (0.5 - 3.0)
  coreTurbulence: number;           // Energy surface turbulence and flare intensity
  rotationSpeedMultiplier: number; // Multiplier for orbital ring and particle rotation
  particleSpeedMultiplier: number; // Velocity multiplier for particles
  particleTurbulence: number;       // Jitter / chaotic brownian motion of particles
  particleSwarmRadius: number;      // Spread radius of outer particle cloud
  particleFlowDirection: "orbital" | "converging" | "diverging" | "chaotic" | "wave";
  particleFlowMode: ParticleFlowMode; // Specialized state-specific behavior mode
  transitionDuration: number;       // Duration of state transition in ms (300 - 800)
  energyDistortion: number;         // Non-spherical plasma warp factor (0.0 - 1.0)
  outerStructureScale: number;      // Dynamic scale of outer rings & HUD framing (0.9 - 1.4)
  innerFilamentSpeed: number;       // Speed of internal core plasma circulation (0.5 - 3.0)
  particleDensityFactor: number;    // Active particle ratio (0.4 for calm IDLE, 1.0 for active)
  speechHarmonicDepth: number;      // Simulated speech vocal breathing depth (0.0 - 1.0)
  ringTiltMultiplier: number;       // Dynamic gyroscopic wobble / precession
  hudAlpha: number;                 // HUD geometry opacity (0.0 - 1.0)
  hudActivityText: string;          // Fallback display text for telemetry badge
  glowIntensityMultiplier: number;  // Bloom & radial glow brightness factor
  constellationLines: boolean;      // Render connecting lines between close particles
}

export interface QualityConfig {
  particleCount: number;
  ringCount: number;
  maxConstellationLines: number;
  glowBlurSteps: number;
  enableDynamicShadows: boolean;
  targetFps: number;
  dprLimit: number;
}

export interface AudioMetrics {
  rawVolume: number;
  smoothedVolume: number;
  lowBand: number;
  midBand: number;
  highBand: number;
  speechActivity: number;
  isAudioActive: boolean;
  peakFrequency: number;
  timestamp: number;
}

export interface CoreEngineOptions {
  quality: QualityLevel;
  baseRadius: number;
  glowIntensity: number;
  reducedMotion: boolean;
  interactive: boolean;
  theme: "clear_sky" | "night_sky";
  customScale?: number;
  opacity?: number;
  audioSensitivity?: number;
}

export interface SakiCoreProps {
  state?: SakiState;
  activity?: string;
  theme?: "clear_sky" | "night_sky";
  quality?: QualityLevel;
  opacity?: number;
  scale?: number;
  reducedMotion?: boolean;
  className?: string;
  interactive?: boolean;
  showHudTelemetry?: boolean;
  audioSensitivity?: number;
  onFpsUpdate?: (fps: number) => void;
}
