import React from "react";
import { MoonGlowProps } from "./types";

/**
 * MoonGlow Component
 * Night sky celestial body with soft lunar corona, crater silhouettes, and subtle starfield.
 */
export default function MoonGlow({ reducedMotion = false }: MoonGlowProps) {
  return (
    <div
      className="absolute top-[8%] right-[14%] w-60 h-60 pointer-events-none -z-5 select-none"
      aria-hidden="true"
    >
      {/* 1. Outer Lunar Aura */}
      <div className={`absolute inset-0 rounded-full bg-gradient-radial from-slate-200/20 via-sky-950/20 to-transparent blur-2xl transform scale-125 ${reducedMotion ? "" : "animate-pulse"}`} />

      {/* 2. Moon Body */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 bg-[#fdfbf7] rounded-full blur-[1px] shadow-[0_0_60px_rgba(253,251,247,0.35)] opacity-95">
        {/* Crater silhouettes */}
        <div className="absolute top-3 left-4 w-14 h-14 bg-[#ede8d5] rounded-full opacity-35 blur-[1px]" />
        <div className="absolute top-8 left-10 w-8 h-8 bg-[#dfd7be] rounded-full opacity-25 blur-[1px]" />
      </div>

      {/* 3. Cosmic Starfield Particles */}
      <div className="fixed inset-0 pointer-events-none -z-6 opacity-75">
        <div className="absolute top-[12%] left-[8%] w-1.5 h-1.5 bg-white rounded-full opacity-80 shadow-[0_0_4px_white]" />
        <div className="absolute top-[22%] left-[28%] w-1 h-1 bg-white rounded-full opacity-60" />
        <div className="absolute top-[8%] left-[52%] w-1.5 h-1.5 bg-white rounded-full opacity-90 shadow-[0_0_6px_white]" />
        <div className="absolute top-[26%] left-[68%] w-1 h-1 bg-white rounded-full opacity-50" />
        <div className="absolute top-[14%] left-[82%] w-2 h-2 bg-white rounded-full opacity-80 shadow-[0_0_6px_white]" />
        <div className="absolute top-[34%] left-[18%] w-1 h-1 bg-white rounded-full opacity-40" />
        <div className="absolute top-[40%] left-[58%] w-1.5 h-1.5 bg-white rounded-full opacity-75" />
        <div className="absolute top-[18%] left-[92%] w-1 h-1 bg-white rounded-full opacity-65" />
      </div>
    </div>
  );
}
