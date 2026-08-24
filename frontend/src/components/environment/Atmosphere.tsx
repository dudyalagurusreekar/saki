import React from "react";
import { AtmosphereProps } from "./types";

/**
 * Atmosphere Component
 * Dynamic sky backdrop rendering atmospheric gradients, diurnal horizon glow,
 * and ambient daylight diffusion.
 */
export default function Atmosphere({
  theme = "clear_sky",
}: AtmosphereProps) {
  const isNight = theme === "night_sky";

  return (
    <div
      className={`fixed inset-0 -z-10 overflow-hidden pointer-events-none transition-all duration-700 select-none ${
        isNight
          ? "bg-gradient-to-b from-[#080d1a] via-[#0f172a] to-[#1e293b]"
          : "bg-gradient-to-b from-[#38bdf8] via-[#7dd3fc] to-[#e0f2fe]"
      }`}
      aria-hidden="true"
    >
      {/* 1. Daytime Horizon Sunlight Diffusion Scattering */}
      {!isNight && (
        <div className="absolute inset-x-0 bottom-0 h-[45vh] bg-gradient-to-t from-white/75 via-sky-100/40 to-transparent pointer-events-none" />
      )}

      {/* 2. Daytime Upper Zenith Deep Blue Veil */}
      {!isNight && (
        <div className="absolute inset-x-0 top-0 h-[30vh] bg-gradient-to-b from-sky-600/20 via-sky-400/10 to-transparent pointer-events-none" />
      )}

      {/* 3. Night Ambient Nebula Glow */}
      {isNight && (
        <div className="absolute inset-0 bg-radial from-indigo-950/30 via-transparent to-transparent pointer-events-none" />
      )}
    </div>
  );
}
