/**
 * Saki Core Configuration (Sprint 3)
 * Central declarative definitions for Saki visual states, quality presets,
 * camera parameters, and math constants with specialized state behaviors.
 */

import { SakiState } from "../../../lib/api";
import { StateVisualProfile, QualityConfig, QualityLevel, OrbitalRingDefinition } from "../types";

export const DEFAULT_CAMERA = {
  fov: 60,
  distance: 600,
  near: 10,
  far: 2000,
};

export const QUALITY_CONFIGS: Record<QualityLevel, QualityConfig> = {
  ultra: {
    particleCount: 380,
    ringCount: 6,
    maxConstellationLines: 80,
    glowBlurSteps: 4,
    enableDynamicShadows: true,
    targetFps: 60,
    dprLimit: 2.0,
  },
  high: {
    particleCount: 240,
    ringCount: 5,
    maxConstellationLines: 40,
    glowBlurSteps: 3,
    enableDynamicShadows: true,
    targetFps: 60,
    dprLimit: 1.5,
  },
  medium: {
    particleCount: 140,
    ringCount: 4,
    maxConstellationLines: 20,
    glowBlurSteps: 2,
    enableDynamicShadows: false,
    targetFps: 60,
    dprLimit: 1.25,
  },
  low: {
    particleCount: 70,
    ringCount: 3,
    maxConstellationLines: 0,
    glowBlurSteps: 1,
    enableDynamicShadows: false,
    targetFps: 30,
    dprLimit: 1.0,
  },
  auto: {
    particleCount: 200,
    ringCount: 4,
    maxConstellationLines: 30,
    glowBlurSteps: 2,
    enableDynamicShadows: true,
    targetFps: 60,
    dprLimit: 1.5,
  },
};

/**
 * Highly refined visual profiles for all 10 authoritative Saki states
 */
export const STATE_VISUAL_PROFILES: Record<SakiState, StateVisualProfile> = {
  IDLE: {
    name: "IDLE",
    primaryColor: { r: 245, g: 248, b: 255, a: 0.92 },    // Neutral Soft White
    secondaryColor: { r: 205, g: 220, b: 245, a: 0.80 },  // Silver Ice
    accentColor: { r: 255, g: 255, b: 255, a: 1.0 },      // Pure Luminous White
    ambientBackdrop: { r: 15, g: 20, b: 35, a: 0.35 },    // Dim Deep Space
    coreRadiusMultiplier: 1.0,
    corePulsingSpeed: 0.7,                                // Slow serene breathing
    coreTurbulence: 0.18,                                 // Minimal turbulence
    rotationSpeedMultiplier: 0.75,                        // Gentle orbital rotation
    particleSpeedMultiplier: 0.65,
    particleTurbulence: 0.15,
    particleSwarmRadius: 1.0,
    particleFlowDirection: "orbital",
    particleFlowMode: "orbital",                          // Calm baseline orbit
    transitionDuration: 650,                              // Smooth deliberate easing
    energyDistortion: 0.1,                                // Uniform spherical harmony
    outerStructureScale: 1.0,
    innerFilamentSpeed: 0.8,
    particleDensityFactor: 0.45,                          // Low particle activity
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 1.0,
    hudAlpha: 0.65,
    hudActivityText: "SYSTEM IDLE // SERENE ORBIT",
    glowIntensityMultiplier: 1.0,
    constellationLines: false,
  },

  LISTENING: {
    name: "LISTENING",
    primaryColor: { r: 16, g: 185, b: 129, a: 0.95 },    // 🟢 Green / Emerald
    secondaryColor: { r: 52, g: 211, b: 153, a: 0.85 },  // Mint Green
    accentColor: { r: 110, g: 231, b: 183, a: 1.0 },     // Luminous Mint
    ambientBackdrop: { r: 6, g: 44, b: 35, a: 0.45 },
    coreRadiusMultiplier: 1.15,
    corePulsingSpeed: 1.5,
    coreTurbulence: 0.35,
    rotationSpeedMultiplier: 1.1,
    particleSpeedMultiplier: 1.25,                        // Responsive particle sensitivity
    particleTurbulence: 0.3,
    particleSwarmRadius: 1.25,
    particleFlowDirection: "converging",
    particleFlowMode: "receptive_expand",                 // Outer structure expands toward interaction
    transitionDuration: 450,
    energyDistortion: 0.25,
    outerStructureScale: 1.22,                            // Subtly expanded outer envelope
    innerFilamentSpeed: 1.3,
    particleDensityFactor: 0.85,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 1.15,
    hudAlpha: 0.85,
    hudActivityText: "AUDIO SENSING // RECEPTIVE ENVELOPE",
    glowIntensityMultiplier: 1.25,
    constellationLines: true,
  },

  PROCESSING: {
    name: "PROCESSING",
    primaryColor: { r: 245, g: 158, b: 11, a: 0.95 },    // 🟡 Warm Amber / Gold
    secondaryColor: { r: 251, g: 191, b: 36, a: 0.85 },  // Gold
    accentColor: { r: 253, g: 230, b: 138, a: 1.0 },     // Bright Sunlight
    ambientBackdrop: { r: 45, g: 26, b: 5, a: 0.45 },
    coreRadiusMultiplier: 1.2,
    corePulsingSpeed: 2.1,                                // Controlled energy buildup
    coreTurbulence: 0.55,
    rotationSpeedMultiplier: 1.6,
    particleSpeedMultiplier: 1.8,
    particleTurbulence: 0.45,
    particleSwarmRadius: 1.08,
    particleFlowDirection: "converging",
    particleFlowMode: "converging_prep",                  // Stream inward while preparing response
    transitionDuration: 400,
    energyDistortion: 0.35,
    outerStructureScale: 1.05,
    innerFilamentSpeed: 1.9,
    particleDensityFactor: 0.9,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 1.35,
    hudAlpha: 0.9,
    hudActivityText: "DATA INGESTION // PREPARING RESPONSE",
    glowIntensityMultiplier: 1.35,
    constellationLines: false,
  },

  THINKING: {
    name: "THINKING",
    primaryColor: { r: 245, g: 190, b: 11, a: 0.95 },    // 🟡 Yellow / Gold Energy
    secondaryColor: { r: 251, g: 191, b: 36, a: 0.85 },  // Warm Gold
    accentColor: { r: 254, g: 240, b: 138, a: 1.0 },     // Luminous Gold
    ambientBackdrop: { r: 45, g: 30, b: 5, a: 0.5 },
    coreRadiusMultiplier: 1.3,
    corePulsingSpeed: 1.85,
    coreTurbulence: 0.8,                                  // Strong internal energy movement
    rotationSpeedMultiplier: 1.85,                        // Pronounced orbital rotation
    particleSpeedMultiplier: 1.6,
    particleTurbulence: 0.85,                             // Layered neural swirl
    particleSwarmRadius: 1.3,
    particleFlowDirection: "chaotic",
    particleFlowMode: "neural_swirl",                     // Multi-frequency layered particle swirl
    transitionDuration: 500,
    energyDistortion: 0.6,                                 // Dynamic plasma lobes
    outerStructureScale: 1.12,
    innerFilamentSpeed: 2.5,                              // High-speed internal energy circulation
    particleDensityFactor: 1.0,                            // Full particle engagement
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 1.65,
    hudAlpha: 0.95,
    hudActivityText: "NEURAL REASONING // LAYERED COGNITION",
    glowIntensityMultiplier: 1.45,
    constellationLines: true,
  },

  SEARCHING: {
    name: "SEARCHING",
    primaryColor: { r: 59, g: 130, b: 246, a: 0.95 },    // 🔵 Electric Blue
    secondaryColor: { r: 96, g: 165, b: 250, a: 0.85 },  // Sky Blue
    accentColor: { r: 191, g: 219, b: 254, a: 1.0 },     // Radiant Light Blue
    ambientBackdrop: { r: 8, g: 30, b: 55, a: 0.5 },
    coreRadiusMultiplier: 1.12,
    corePulsingSpeed: 2.3,
    coreTurbulence: 0.45,
    rotationSpeedMultiplier: 2.1,                         // Directional orbital velocity
    particleSpeedMultiplier: 2.3,
    particleTurbulence: 0.4,
    particleSwarmRadius: 1.45,
    particleFlowDirection: "diverging",
    particleFlowMode: "search_radar",                     // Directional radar sweep & probe rays
    transitionDuration: 450,
    energyDistortion: 0.3,
    outerStructureScale: 1.18,
    innerFilamentSpeed: 2.0,
    particleDensityFactor: 0.95,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 0.75,                             // Aligned scanning rings
    hudAlpha: 0.95,
    hudActivityText: "WORLD ACCESS // DIRECTIONAL RADAR SWEEP",
    glowIntensityMultiplier: 1.35,
    constellationLines: false,
  },

  VISION: {
    name: "VISION",
    primaryColor: { r: 168, g: 85, b: 247, a: 0.95 },    // 🟣 Vibrant Purple
    secondaryColor: { r: 192, g: 132, b: 252, a: 0.85 }, // Lilac Purple
    accentColor: { r: 243, g: 232, b: 255, a: 1.0 },     // Luminous Violet
    ambientBackdrop: { r: 35, g: 12, b: 45, a: 0.45 },
    coreRadiusMultiplier: 1.22,
    corePulsingSpeed: 1.65,
    coreTurbulence: 0.3,
    rotationSpeedMultiplier: 1.25,
    particleSpeedMultiplier: 1.2,
    particleTurbulence: 0.25,
    particleSwarmRadius: 0.9,                             // Focal optical contraction
    particleFlowDirection: "converging",
    particleFlowMode: "optical_scan",                     // Outer scanning structure emphasis
    transitionDuration: 450,
    energyDistortion: 0.2,
    outerStructureScale: 1.32,                            // Emphasized outer scanning aperture
    innerFilamentSpeed: 1.2,
    particleDensityFactor: 0.85,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 1.1,
    hudAlpha: 1.0,                                        // Maximum HUD reticle visibility
    hudActivityText: "MULTIMODAL VISION // OPTICAL APERTURE",
    glowIntensityMultiplier: 1.3,
    constellationLines: true,
  },

  REMEMBERING: {
    name: "REMEMBERING",
    primaryColor: { r: 20, g: 184, b: 166, a: 0.95 },    // 💠 Cyan / Teal
    secondaryColor: { r: 45, g: 212, b: 191, a: 0.85 },  // Aquamarine
    accentColor: { r: 204, g: 251, b: 241, a: 1.0 },     // Opal Cyan
    ambientBackdrop: { r: 4, g: 35, b: 35, a: 0.45 },
    coreRadiusMultiplier: 1.08,
    corePulsingSpeed: 1.15,
    coreTurbulence: 0.28,
    rotationSpeedMultiplier: 0.85,
    particleSpeedMultiplier: 0.85,
    particleTurbulence: 0.22,
    particleSwarmRadius: 1.15,
    particleFlowDirection: "orbital",
    particleFlowMode: "inward_recall",                    // Subtle inward memory recall vortex
    transitionDuration: 600,
    energyDistortion: 0.2,
    outerStructureScale: 0.98,
    innerFilamentSpeed: 1.0,
    particleDensityFactor: 0.8,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 0.95,
    hudAlpha: 0.85,
    hudActivityText: "MEMORY RETRIEVAL // INWARD RECALL VORTEX",
    glowIntensityMultiplier: 1.2,
    constellationLines: true,                             // Crystalline memory connections
  },

  ACTING: {
    name: "ACTING",
    primaryColor: { r: 249, g: 115, b: 22, a: 0.95 },    // 🟠 Kinetic Orange
    secondaryColor: { r: 251, g: 146, b: 60, a: 0.85 },  // Warm Amber
    accentColor: { r: 254, g: 215, b: 170, a: 1.0 },     // Solar Flare
    ambientBackdrop: { r: 50, g: 18, b: 8, a: 0.5 },
    coreRadiusMultiplier: 1.35,
    corePulsingSpeed: 2.5,
    coreTurbulence: 0.8,
    rotationSpeedMultiplier: 2.2,                         // High-velocity orbital thrust
    particleSpeedMultiplier: 2.5,
    particleTurbulence: 0.65,
    particleSwarmRadius: 1.35,
    particleFlowDirection: "diverging",
    particleFlowMode: "kinetic_vector",                   // Controlled directional activity vectors
    transitionDuration: 380,
    energyDistortion: 0.55,
    outerStructureScale: 1.15,
    innerFilamentSpeed: 2.6,
    particleDensityFactor: 1.0,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 1.75,
    hudAlpha: 0.95,
    hudActivityText: "CAPABILITY EXECUTION // DIRECTIONAL VECTORS",
    glowIntensityMultiplier: 1.5,
    constellationLines: false,
  },

  SPEAKING: {
    name: "SPEAKING",
    primaryColor: { r: 239, g: 68, b: 68, a: 0.95 },    // 🔴 Warm Red / Radiant Speech
    secondaryColor: { r: 248, g: 113, b: 113, a: 0.85 }, // Coral Red
    accentColor: { r: 254, g: 202, b: 202, a: 1.0 },     // Luminous Speech Core
    ambientBackdrop: { r: 55, g: 15, b: 15, a: 0.45 },
    coreRadiusMultiplier: 1.28,
    corePulsingSpeed: 2.6,                                // Harmonic speech resonance
    coreTurbulence: 0.75,
    rotationSpeedMultiplier: 1.75,
    particleSpeedMultiplier: 2.0,
    particleTurbulence: 0.7,
    particleSwarmRadius: 1.38,
    particleFlowDirection: "diverging",
    particleFlowMode: "speech_harmonic_pulse",            // Outward harmonic speech bursts & respiration
    transitionDuration: 300,
    energyDistortion: 0.5,
    outerStructureScale: 1.25,                            // Acoustic expansion
    innerFilamentSpeed: 2.4,
    particleDensityFactor: 1.0,
    speechHarmonicDepth: 1.0,                             // Max dynamic audio-reactivity
    ringTiltMultiplier: 1.45,
    hudAlpha: 0.9,
    hudActivityText: "ACOUSTIC SYNTHESIS // SPEECH RESONANCE",
    glowIntensityMultiplier: 1.6,
    constellationLines: true,
  },

  ERROR: {
    name: "ERROR",
    primaryColor: { r: 220, g: 38, b: 38, a: 0.95 },    // ⚠️ Controlled Warning Crimson
    secondaryColor: { r: 239, g: 68, b: 68, a: 0.85 },
    accentColor: { r: 254, g: 226, b: 226, a: 1.0 },
    ambientBackdrop: { r: 45, g: 8, b: 8, a: 0.5 },
    coreRadiusMultiplier: 0.92,
    corePulsingSpeed: 3.2,                                // Rapid alarm oscillation
    coreTurbulence: 0.9,
    rotationSpeedMultiplier: 0.45,                        // Destabilized slow tumble
    particleSpeedMultiplier: 0.8,
    particleTurbulence: 0.95,
    particleSwarmRadius: 0.8,                             // Contracted chaotic shell
    particleFlowDirection: "chaotic",
    particleFlowMode: "restrained_caution",
    transitionDuration: 250,
    energyDistortion: 0.75,                               // Distorted jagged energy
    outerStructureScale: 0.95,
    innerFilamentSpeed: 0.6,
    particleDensityFactor: 0.65,
    speechHarmonicDepth: 0.0,
    ringTiltMultiplier: 2.0,                              // Highly tilted perturbed rings
    hudAlpha: 1.0,
    hudActivityText: "SYSTEM WARNING // CONTROLLED RECOVERY",
    glowIntensityMultiplier: 1.2,
    constellationLines: false,
  },
};

/**
 * Initial 3D orbital rings definition with asymmetrical tilts & speeds
 */
export function createDefaultOrbitalRings(baseRadius: number): OrbitalRingDefinition[] {
  return [
    {
      id: "ring_equatorial",
      radius: baseRadius * 1.35,
      tiltX: 0.25,
      tiltY: 0.1,
      tiltZ: 0.05,
      rotationSpeed: 0.006,
      currentAngle: 0,
      dashArray: [16, 8, 4, 8],
      lineWidth: 1.6,
      color: { r: 99, g: 102, b: 241, a: 0.65 },
      hasNodes: true,
      nodes: [
        { angle: 0, size: 3.5, speed: 0.012, pulsePhase: 0 },
        { angle: Math.PI, size: 2.5, speed: 0.012, pulsePhase: Math.PI },
      ],
      showTicks: true,
      tickCount: 36,
      asymmetryFactor: 1.02,
    },
    {
      id: "ring_polar_inclined",
      radius: baseRadius * 1.75,
      tiltX: 1.15,
      tiltY: -0.45,
      tiltZ: 0.35,
      rotationSpeed: -0.008,
      currentAngle: Math.PI / 4,
      dashArray: [30, 12, 6, 12],
      lineWidth: 1.4,
      color: { r: 56, g: 189, b: 248, a: 0.55 },
      hasNodes: true,
      nodes: [
        { angle: Math.PI / 3, size: 3.0, speed: -0.014, pulsePhase: 1.5 },
        { angle: (4 * Math.PI) / 3, size: 2.0, speed: -0.014, pulsePhase: 4.5 },
      ],
      showTicks: true,
      tickCount: 24,
      asymmetryFactor: 0.96,
    },
    {
      id: "ring_gyroscopic_high",
      radius: baseRadius * 2.15,
      tiltX: -0.75,
      tiltY: 0.85,
      tiltZ: -0.5,
      rotationSpeed: 0.005,
      currentAngle: Math.PI / 2,
      dashArray: [8, 8],
      lineWidth: 1.2,
      color: { r: 168, g: 85, b: 247, a: 0.45 },
      hasNodes: true,
      nodes: [
        { angle: (2 * Math.PI) / 3, size: 2.5, speed: 0.009, pulsePhase: 2.8 },
      ],
      showTicks: false,
      tickCount: 16,
      asymmetryFactor: 1.05,
    },
    {
      id: "ring_outer_telemetry",
      radius: baseRadius * 2.65,
      tiltX: 0.4,
      tiltY: -0.3,
      tiltZ: 0.65,
      rotationSpeed: -0.004,
      currentAngle: Math.PI * 0.75,
      dashArray: [45, 15, 10, 15, 10, 15],
      lineWidth: 1.0,
      color: { r: 99, g: 102, b: 241, a: 0.35 },
      hasNodes: true,
      nodes: [
        { angle: 0.5, size: 2.2, speed: -0.007, pulsePhase: 0.8 },
        { angle: 3.5, size: 2.2, speed: -0.007, pulsePhase: 3.8 },
      ],
      showTicks: true,
      tickCount: 48,
      asymmetryFactor: 0.98,
    },
    {
      id: "ring_innermost_fast",
      radius: baseRadius * 1.05,
      tiltX: 0.6,
      tiltY: 0.6,
      tiltZ: 0.1,
      rotationSpeed: 0.015,
      currentAngle: 0,
      dashArray: [6, 6],
      lineWidth: 1.8,
      color: { r: 255, g: 255, b: 255, a: 0.75 },
      hasNodes: false,
      nodes: [],
      showTicks: false,
      tickCount: 12,
      asymmetryFactor: 1.0,
    },
    {
      id: "ring_far_horizon",
      radius: baseRadius * 3.1,
      tiltX: 0.15,
      tiltY: 0.05,
      tiltZ: -0.2,
      rotationSpeed: 0.002,
      currentAngle: 0,
      dashArray: [60, 40],
      lineWidth: 0.8,
      color: { r: 56, g: 189, b: 248, a: 0.25 },
      hasNodes: false,
      nodes: [],
      showTicks: true,
      tickCount: 64,
      asymmetryFactor: 1.01,
    }
  ];
}
