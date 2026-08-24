import React, { useMemo } from "react";
import { CloudLayerProps, CloudDefinition } from "./types";

/**
 * CloudLayer Component (Sprint 13)
 * Multi-depth procedural drifting cloud system with 3 distinct altitude planes:
 * 1. High Cirrus (slowest, highest altitude, ethereal soft blur)
 * 2. Mid Cumulus (medium speed, realistic multi-puff volumetric clouds)
 * 3. Low Stratus (faster gentle drifter, airy translucency)
 * 
 * Hardware-accelerated with CSS translate3d, negative entry offsets for immediate
 * full-screen coverage, and automatic reduced-motion stabilization.
 */
export default function CloudLayer({
  theme = "clear_sky",
  reducedMotion = false,
  density = "medium",
}: CloudLayerProps) {
  const isNight = theme === "night_sky";

  // Declarative procedural cloud configurations across 3 depth planes
  const clouds: CloudDefinition[] = useMemo(() => {
    return [
      // -------------------------------------------------------------
      // PLANE 1: High Cirrus Layer (Ethereal, high altitude, slowest)
      // -------------------------------------------------------------
      {
        id: "cirrus-1",
        layer: "high_cirrus",
        topPercent: 8,
        widthPx: 380,
        heightPx: 100,
        scale: 1.1,
        opacity: isNight ? 0.25 : 0.88,
        durationSec: 140,
        delaySec: -25, // Staggered initial position
        puffs: [
          { topOffsetPx: -35, leftOffsetPx: 50, sizePx: 110, opacity: 0.9 },
          { topOffsetPx: -50, leftOffsetPx: 140, sizePx: 135, opacity: 0.95 },
          { topOffsetPx: -30, leftOffsetPx: 230, sizePx: 105, opacity: 0.85 },
          { topOffsetPx: -15, leftOffsetPx: 300, sizePx: 80, opacity: 0.75 },
        ],
      },
      {
        id: "cirrus-2",
        layer: "high_cirrus",
        topPercent: 18,
        widthPx: 320,
        heightPx: 85,
        scale: 0.95,
        opacity: isNight ? 0.20 : 0.82,
        durationSec: 160,
        delaySec: -95, // Opposite side of sky initially
        puffs: [
          { topOffsetPx: -25, leftOffsetPx: 40, sizePx: 90, opacity: 0.85 },
          { topOffsetPx: -45, leftOffsetPx: 115, sizePx: 120, opacity: 0.95 },
          { topOffsetPx: -30, leftOffsetPx: 200, sizePx: 95, opacity: 0.8 },
        ],
      },

      // -------------------------------------------------------------
      // PLANE 2: Mid Cumulus Layer (Volumetric clusters, realistic form)
      // -------------------------------------------------------------
      {
        id: "cumulus-1",
        layer: "mid_cumulus",
        topPercent: 26,
        widthPx: 340,
        heightPx: 95,
        scale: 1.0,
        opacity: isNight ? 0.30 : 0.92,
        durationSec: 90,
        delaySec: -45,
        puffs: [
          { topOffsetPx: -30, leftOffsetPx: 35, sizePx: 100, opacity: 0.9 },
          { topOffsetPx: -55, leftOffsetPx: 110, sizePx: 130, opacity: 0.98 },
          { topOffsetPx: -40, leftOffsetPx: 195, sizePx: 115, opacity: 0.92 },
          { topOffsetPx: -20, leftOffsetPx: 265, sizePx: 85, opacity: 0.85 },
        ],
      },
      {
        id: "cumulus-2",
        layer: "mid_cumulus",
        topPercent: 38,
        widthPx: 290,
        heightPx: 80,
        scale: 0.9,
        opacity: isNight ? 0.22 : 0.85,
        durationSec: 105,
        delaySec: -75,
        puffs: [
          { topOffsetPx: -25, leftOffsetPx: 30, sizePx: 85, opacity: 0.88 },
          { topOffsetPx: -45, leftOffsetPx: 95, sizePx: 115, opacity: 0.95 },
          { topOffsetPx: -30, leftOffsetPx: 175, sizePx: 95, opacity: 0.85 },
        ],
      },

      // -------------------------------------------------------------
      // PLANE 3: Low Stratus Layer (Light foreground drifter, airy)
      // -------------------------------------------------------------
      {
        id: "stratus-1",
        layer: "low_stratus",
        topPercent: 4,
        widthPx: 420,
        heightPx: 115,
        scale: 1.2,
        opacity: isNight ? 0.35 : 0.95,
        durationSec: 65,
        delaySec: -12,
        puffs: [
          { topOffsetPx: -45, leftOffsetPx: 50, sizePx: 125, opacity: 0.92 },
          { topOffsetPx: -65, leftOffsetPx: 155, sizePx: 155, opacity: 0.98 },
          { topOffsetPx: -45, leftOffsetPx: 265, sizePx: 130, opacity: 0.9 },
          { topOffsetPx: -25, leftOffsetPx: 345, sizePx: 95, opacity: 0.8 },
        ],
      },
      {
        id: "stratus-2",
        layer: "low_stratus",
        topPercent: 48,
        widthPx: 360,
        heightPx: 90,
        scale: 1.05,
        opacity: isNight ? 0.18 : 0.78,
        durationSec: 75,
        delaySec: -50,
        puffs: [
          { topOffsetPx: -30, leftOffsetPx: 40, sizePx: 95, opacity: 0.85 },
          { topOffsetPx: -50, leftOffsetPx: 125, sizePx: 125, opacity: 0.92 },
          { topOffsetPx: -35, leftOffsetPx: 215, sizePx: 105, opacity: 0.85 },
        ],
      },
    ];
  }, [isNight]);

  // Filter clouds based on density configuration
  const activeClouds = useMemo(() => {
    if (density === "low") {
      return clouds.filter((c) => c.layer !== "low_stratus");
    }
    return clouds;
  }, [clouds, density]);

  // Color palette for procedural puffs
  const baseCloudColor = isNight
    ? "bg-slate-800/40 text-slate-700 shadow-[0_4px_20px_rgba(15,23,42,0.4)]"
    : "bg-white text-sky-100 shadow-[0_6px_25px_rgba(255,255,255,0.7)]";

  const puffColor = isNight
    ? "bg-slate-800/45"
    : "bg-gradient-to-b from-white via-white to-sky-50/90";

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden -z-8 select-none"
      aria-hidden="true"
    >
      {activeClouds.map((c, idx) => {
        const animationClass = reducedMotion
          ? ""
          : c.layer === "high_cirrus"
          ? "animate-cloud-drift-cirrus"
          : c.layer === "mid_cumulus"
          ? "animate-cloud-drift-cumulus"
          : "animate-cloud-drift-stratus";

        // Static balanced fallback positions for reduced motion
        const staticLefts = ["12%", "55%", "25%", "68%", "5%", "45%"];
        const staticLeft = staticLefts[idx % staticLefts.length];

        return (
          <div
            key={c.id}
            className={`absolute flex items-center justify-center will-change-transform ${animationClass}`}
            style={{
              top: `${c.topPercent}%`,
              left: reducedMotion ? staticLeft : "-450px",
              width: `${c.widthPx}px`,
              height: `${c.heightPx}px`,
              opacity: c.opacity,
              animationDuration: `${c.durationSec}s`,
              animationDelay: `${c.delaySec}s`,
              filter: isNight ? "blur(2.5px)" : "blur(1.5px)",
              transform: `scale(${c.scale}) translateZ(0)`,
            }}
          >
            {/* Base Pill Foundation */}
            <div
              className={`w-full h-full rounded-full ${baseCloudColor} relative`}
            >
              {/* Procedural Volumetric Puffs */}
              {c.puffs.map((puff, pIdx) => (
                <div
                  key={`${c.id}-puff-${pIdx}`}
                  className={`absolute rounded-full ${puffColor}`}
                  style={{
                    top: `${puff.topOffsetPx}px`,
                    left: `${puff.leftOffsetPx}px`,
                    width: `${puff.sizePx}px`,
                    height: `${puff.sizePx}px`,
                    opacity: puff.opacity,
                  }}
                />
              ))}

              {/* Daytime subtle sunlight rim highlight */}
              {!isNight && (
                <div className="absolute inset-x-4 top-1 h-3 rounded-full bg-white/80 blur-xs" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
