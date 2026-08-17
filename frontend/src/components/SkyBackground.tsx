interface SkyBackgroundProps {
  theme?: "clear_sky" | "night_sky";
  reducedMotion?: boolean;
}

export default function SkyBackground({
  theme = "clear_sky",
  reducedMotion = false
}: SkyBackgroundProps) {
  const isNight = theme === "night_sky";

  if (isNight) {
    return (
      <div 
        className="fixed inset-0 -z-10 overflow-hidden pointer-events-none transition-colors duration-700 bg-gradient-to-b from-[#0b132b] via-[#1c2541] to-[#3a506b]"
        aria-hidden="true"
      >
        {/* Soft Moon Glow */}
        <div className="absolute top-[10%] right-[15%] w-28 h-28 bg-[#fdfbf7] rounded-full blur-[2px] shadow-[0_0_80px_rgba(253,251,247,0.4)] opacity-95">
          <div className="absolute top-2 left-3 w-20 h-20 bg-[#f4ebd0] rounded-full opacity-30 blur-[1px]"></div>
        </div>

        {/* Subtle Stars */}
        <div className="absolute inset-0 opacity-70">
          <div className="absolute top-[12%] left-[10%] w-1.5 h-1.5 bg-white rounded-full opacity-80 shadow-[0_0_4px_white]"></div>
          <div className="absolute top-[20%] left-[30%] w-1 h-1 bg-white rounded-full opacity-60"></div>
          <div className="absolute top-[8%] left-[55%] w-1.5 h-1.5 bg-white rounded-full opacity-90 shadow-[0_0_6px_white]"></div>
          <div className="absolute top-[28%] left-[70%] w-1 h-1 bg-white rounded-full opacity-50"></div>
          <div className="absolute top-[15%] left-[85%] w-2 h-2 bg-white rounded-full opacity-80 shadow-[0_0_6px_white]"></div>
          <div className="absolute top-[35%] left-[20%] w-1 h-1 bg-white rounded-full opacity-40"></div>
          <div className="absolute top-[42%] left-[60%] w-1.5 h-1.5 bg-white rounded-full opacity-75"></div>
        </div>

        {/* Night Clouds */}
        <div 
          className={`absolute top-[18%] w-[320px] h-[95px] bg-[#1c2541]/40 rounded-full blur-[3px] flex items-center justify-center ${
            reducedMotion ? "left-[15%]" : "animate-drift-slow"
          }`}
        >
          <div className="absolute top-[-30px] left-[40px] w-[100px] h-[100px] bg-[#1c2541]/40 rounded-full"></div>
          <div className="absolute top-[-50px] right-[60px] w-[120px] h-[120px] bg-[#1c2541]/40 rounded-full"></div>
        </div>

        <div 
          className={`absolute top-[35%] w-[260px] h-[75px] bg-[#3a506b]/30 rounded-full blur-[2px] ${
            reducedMotion ? "left-[45%]" : "animate-drift-medium"
          }`} 
          style={!reducedMotion ? { animationDelay: "-30s" } : undefined}
        >
          <div className="absolute top-[-20px] left-[30px] w-[80px] h-[80px] bg-[#3a506b]/30 rounded-full"></div>
          <div className="absolute top-[-40px] right-[50px] w-[100px] h-[100px] bg-[#3a506b]/30 rounded-full"></div>
        </div>
      </div>
    );
  }

  // Clear Sky (Daytime Default)
  return (
    <div 
      className="fixed inset-0 -z-10 overflow-hidden pointer-events-none transition-colors duration-700 bg-gradient-to-b from-[#90cdf4] via-[#bae6fd] to-[#e0f2fe]"
      aria-hidden="true"
    >
      {/* Subtle Sun Glow */}
      <div className="absolute top-[8%] left-[18%] w-36 h-36 bg-yellow-50/90 rounded-full blur-[6px] shadow-[0_0_120px_rgba(255,255,180,0.85)]"></div>

      {/* Cloud 1 - Slow & High */}
      <div 
        className={`absolute top-[14%] w-[320px] h-[95px] bg-white/90 rounded-full blur-[2px] shadow-sm flex items-center justify-center ${
          reducedMotion ? "left-[10%]" : "animate-drift-slow"
        }`}
      >
        <div className="absolute top-[-30px] left-[40px] w-[100px] h-[100px] bg-white/90 rounded-full"></div>
        <div className="absolute top-[-50px] right-[60px] w-[120px] h-[120px] bg-white/90 rounded-full"></div>
      </div>

      {/* Cloud 2 - Medium Speed */}
      <div 
        className={`absolute top-[30%] w-[260px] h-[75px] bg-white/80 rounded-full blur-[1px] ${
          reducedMotion ? "left-[50%]" : "animate-drift-medium"
        }`} 
        style={!reducedMotion ? { animationDelay: "-25s" } : undefined}
      >
        <div className="absolute top-[-20px] left-[30px] w-[80px] h-[80px] bg-white/80 rounded-full"></div>
        <div className="absolute top-[-40px] right-[50px] w-[100px] h-[100px] bg-white/80 rounded-full"></div>
      </div>

      {/* Cloud 3 - Foreground Drifter */}
      <div 
        className={`absolute top-[5%] w-[380px] h-[110px] bg-white/95 rounded-full blur-[3px] ${
          reducedMotion ? "left-[70%]" : "animate-drift-fast"
        }`} 
        style={!reducedMotion ? { animationDelay: "-10s" } : undefined}
      >
        <div className="absolute top-[-40px] left-[55px] w-[110px] h-[110px] bg-white/95 rounded-full"></div>
        <div className="absolute top-[-55px] right-[75px] w-[140px] h-[140px] bg-white/95 rounded-full"></div>
      </div>
    </div>
  );
}
