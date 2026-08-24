import React from "react";
import { SunGlowProps } from "./types";

/**
 * SunGlow Component
 * Procedural daytime celestial illumination with multi-stage radial corona,
 * warm atmospheric scattering, and subtle ambient daylight diffusion.
 */
export default function SunGlow({ reducedMotion = false }: SunGlowProps) {
  return (
    <div
      className="absolute top-[6%] left-[16%] w-72 h-72 pointer-events-none -z-5 select-none"
      aria-hidden="true"
    >
      {/* 1. Outer Atmospheric Daylight Diffusion Halo */}
      <div 
        className={`absolute inset-0 rounded-full bg-gradient-radial from-amber-100/40 via-sky-200/25 to-transparent blur-3xl transform scale-150 ${
          reducedMotion ? "" : "animate-sun-pulse-slow"
        }`}
      />

      {/* 2. Secondary Radiant Corona Ring */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 rounded-full bg-gradient-radial from-yellow-100/70 via-amber-200/30 to-transparent blur-xl shadow-[0_0_90px_rgba(254,240,138,0.55)]"
      />

      {/* 3. Central Luminous Solar Core */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 rounded-full bg-gradient-to-tr from-white via-yellow-50 to-amber-100 blur-[2px] shadow-[0_0_70px_rgba(255,255,255,0.9)] opacity-95"
      >
        {/* Core highlight */}
        <div className="absolute top-2 left-3 w-16 h-16 rounded-full bg-white/90 blur-[1px]" />
      </div>

      {/* 4. Subtle Atmospheric Lens Shimmer Flare */}
      {!reducedMotion && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-1 bg-gradient-to-r from-transparent via-amber-100/25 to-transparent rotate-45 blur-xs pointer-events-none" />
      )}
    </div>
  );
}
