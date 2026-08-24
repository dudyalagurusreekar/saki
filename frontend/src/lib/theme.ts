/**
 * Saki UI Theme Tokens & Design System (Sprint 13)
 * Authoritative definitions for Night Sky (Dark) and Clear Sky (Light) environments.
 * Defines semantic color tokens, glassmorphism parameters, atmospheric properties,
 * and high-contrast typography scales for both themes.
 */

export type SakiTheme = "clear_sky" | "night_sky";

export interface ThemeColors {
  backgroundGradient: string;
  panelBackground: string;
  panelBorder: string;
  panelBorderHover: string;
  panelGlow: string;
  cardBackground: string;
  cardBorder: string;
  cardHoverBackground: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textAccent: string;
  hudLabel: string;
  cornerBracket: string;
  inputDockBackground: string;
  inputDockBorder: string;
  inputDockFocusBorder: string;
  inputDockGlow: string;
  userBubbleBackground: string;
  userBubbleBorder: string;
  userBubbleText: string;
  aiBubbleBackground: string;
  aiBubbleBorder: string;
  aiBubbleText: string;
  codeBlockBackground: string;
  codeBlockText: string;
}

export interface AtmosphereConfig {
  celestialBody: "sun" | "moon";
  sunGlowColor: string;
  sunHaloRadius: number;
  skyGradientTop: string;
  skyGradientMiddle: string;
  skyGradientBottom: string;
  ambientLightIntensity: number;
  cloudsEnabled: boolean;
  cloudOpacityMultiplier: number;
  starsEnabled: boolean;
}

export interface ThemeDefinition {
  id: SakiTheme;
  name: string;
  tagline: string;
  icon: string;
  colors: ThemeColors;
  atmosphere: AtmosphereConfig;
}

export const THEMES: Record<SakiTheme, ThemeDefinition> = {
  night_sky: {
    id: "night_sky",
    name: "Night Sky",
    tagline: "Cinematic dark cosmic cybernetic environment",
    icon: "🌙",
    colors: {
      backgroundGradient: "from-[#080d1a] via-[#0f172a] to-[#1e293b]",
      panelBackground: "rgba(13, 19, 33, 0.72)",
      panelBorder: "rgba(56, 189, 248, 0.18)",
      panelBorderHover: "rgba(56, 189, 248, 0.45)",
      panelGlow: "0 8px 32px 0 rgba(0, 0, 0, 0.55), 0 0 20px 0 rgba(56, 189, 248, 0.12)",
      cardBackground: "rgba(15, 23, 42, 0.55)",
      cardBorder: "rgba(148, 163, 184, 0.12)",
      cardHoverBackground: "rgba(15, 23, 42, 0.80)",
      textPrimary: "#f8fafc",
      textSecondary: "#cbd5e1",
      textMuted: "#64748b",
      textAccent: "#38bdf8",
      hudLabel: "rgba(56, 189, 248, 0.85)",
      cornerBracket: "rgba(56, 189, 248, 0.60)",
      inputDockBackground: "rgba(11, 17, 30, 0.82)",
      inputDockBorder: "rgba(56, 189, 248, 0.25)",
      inputDockFocusBorder: "rgba(56, 189, 248, 0.60)",
      inputDockGlow: "0 12px 40px rgba(0, 0, 0, 0.65), 0 0 25px rgba(56, 189, 248, 0.15)",
      userBubbleBackground: "rgba(15, 23, 42, 0.80)",
      userBubbleBorder: "rgba(99, 102, 241, 0.35)",
      userBubbleText: "#f1f5f9",
      aiBubbleBackground: "rgba(11, 17, 30, 0.75)",
      aiBubbleBorder: "rgba(56, 189, 248, 0.22)",
      aiBubbleText: "#f1f5f9",
      codeBlockBackground: "rgba(10, 15, 29, 0.92)",
      codeBlockText: "#bae6fd",
    },
    atmosphere: {
      celestialBody: "moon",
      sunGlowColor: "rgba(253, 251, 247, 0.4)",
      sunHaloRadius: 80,
      skyGradientTop: "#080d1a",
      skyGradientMiddle: "#0f172a",
      skyGradientBottom: "#1e293b",
      ambientLightIntensity: 0.3,
      cloudsEnabled: true,
      cloudOpacityMultiplier: 0.35,
      starsEnabled: true,
    },
  },
  clear_sky: {
    id: "clear_sky",
    name: "Clear Sky",
    tagline: "Calm, bright daytime atmosphere with procedural moving clouds and light glass UI",
    icon: "☀️",
    colors: {
      backgroundGradient: "from-[#60a5fa] via-[#93c5fd] to-[#dbeafe]",
      panelBackground: "rgba(255, 255, 255, 0.68)",
      panelBorder: "rgba(14, 165, 233, 0.25)",
      panelBorderHover: "rgba(14, 165, 233, 0.50)",
      panelGlow: "0 8px 32px 0 rgba(14, 165, 233, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.60)",
      cardBackground: "rgba(255, 255, 255, 0.55)",
      cardBorder: "rgba(186, 230, 253, 0.60)",
      cardHoverBackground: "rgba(255, 255, 255, 0.85)",
      textPrimary: "#0f172a",
      textSecondary: "#334155",
      textMuted: "#64748b",
      textAccent: "#0284c7",
      hudLabel: "#0369a1",
      cornerBracket: "rgba(2, 132, 199, 0.55)",
      inputDockBackground: "rgba(255, 255, 255, 0.80)",
      inputDockBorder: "rgba(14, 165, 233, 0.35)",
      inputDockFocusBorder: "rgba(2, 132, 199, 0.70)",
      inputDockGlow: "0 12px 36px rgba(14, 165, 233, 0.18), 0 0 20px rgba(186, 230, 253, 0.40)",
      userBubbleBackground: "rgba(224, 242, 254, 0.85)",
      userBubbleBorder: "rgba(56, 189, 248, 0.45)",
      userBubbleText: "#0c4a6e",
      aiBubbleBackground: "rgba(255, 255, 255, 0.85)",
      aiBubbleBorder: "rgba(186, 230, 253, 0.70)",
      aiBubbleText: "#0f172a",
      codeBlockBackground: "rgba(15, 23, 42, 0.95)",
      codeBlockText: "#e0f2fe",
    },
    atmosphere: {
      celestialBody: "sun",
      sunGlowColor: "rgba(255, 250, 220, 0.85)",
      sunHaloRadius: 140,
      skyGradientTop: "#38bdf8",
      skyGradientMiddle: "#7dd3fc",
      skyGradientBottom: "#e0f2fe",
      ambientLightIntensity: 0.95,
      cloudsEnabled: true,
      cloudOpacityMultiplier: 0.90,
      starsEnabled: false,
    },
  },
};

export function getTheme(theme: SakiTheme = "night_sky"): ThemeDefinition {
  return THEMES[theme] || THEMES.night_sky;
}
