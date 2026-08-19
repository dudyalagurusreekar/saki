import { useState, useEffect } from "react";

interface TopBarProps {
  theme: "clear_sky" | "night_sky";
  onToggleTheme: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isBrainOpen: boolean;
  onToggleBrain: () => void;
  healthStatus?: "Online" | "Degraded" | "Offline";
  mode?: string;
  activeProject?: string;
}

// Time-of-day emoji mapping
function getTimeOfDayEmoji(hour: number): string {
  if (hour >= 0 && hour < 4) return "🌑";
  if (hour >= 4 && hour < 6) return "🌅";
  if (hour >= 6 && hour < 12) return "🌤️";
  if (hour >= 12 && hour < 17) return "☀️";
  if (hour >= 17 && hour < 21) return "🌆";
  return "🌙";
}

export default function TopBar({
  theme,
  onToggleTheme,
  isSidebarOpen,
  onToggleSidebar,
  isBrainOpen,
  onToggleBrain,
  healthStatus = "Online",
  mode = "casual",
  activeProject
}: TopBarProps) {
  const isNight = theme === "night_sky";

  // -------------------------
  // Live Clock State
  // -------------------------
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  const [colonVisible, setColonVisible] = useState(true);

  useEffect(() => {
    // Set initial time after mount to avoid hydration mismatch
    setCurrentTime(new Date());

    const tickInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    const blinkInterval = setInterval(() => {
      setColonVisible((prev) => !prev);
    }, 1000);

    return () => {
      clearInterval(tickInterval);
      clearInterval(blinkInterval);
    };
  }, []);

  const getModeBadge = (m: string) => {
    switch (m) {
      case "builder":
        return { label: "💻 Builder", color: isNight ? "bg-emerald-950/80 text-emerald-300 border-emerald-700" : "bg-emerald-50 text-emerald-700 border-emerald-300" };
      case "support":
        return { label: "❤️ Support", color: isNight ? "bg-rose-950/80 text-rose-300 border-rose-700" : "bg-rose-50 text-rose-700 border-rose-300" };
      case "thinking":
        return { label: "🧠 Thinking", color: isNight ? "bg-indigo-950/80 text-indigo-300 border-indigo-700" : "bg-indigo-50 text-indigo-700 border-indigo-300" };
      case "vision":
        return { label: "👁️ Vision", color: isNight ? "bg-cyan-950/80 text-cyan-300 border-cyan-700" : "bg-cyan-50 text-cyan-700 border-cyan-300" };
      default:
        return { label: "⚡ Casual", color: isNight ? "bg-amber-950/80 text-amber-300 border-amber-700" : "bg-amber-50 text-amber-700 border-amber-300" };
    }
  };

  const getHealthDot = (status: "Online" | "Degraded" | "Offline") => {
    switch (status) {
      case "Online":
        return { dot: "bg-emerald-400", text: "text-emerald-600 dark:text-emerald-400", label: "Online" };
      case "Degraded":
        return { dot: "bg-amber-400", text: "text-amber-600 dark:text-amber-400", label: "Degraded" };
      default:
        return { dot: "bg-red-400", text: "text-red-600 dark:text-red-400", label: "Offline" };
    }
  };

  const modeBadge = getModeBadge(mode);
  const health = getHealthDot(healthStatus);

  // Format time display
  const formatTime = (date: Date) => {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    const minuteStr = minutes.toString().padStart(2, "0");
    return { hours: hours.toString(), minutes: minuteStr, ampm };
  };

  const formatDate = (date: Date) => {
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${days[date.getDay()]}, ${months[date.getMonth()]} ${date.getDate()}`;
  };

  const timeData = currentTime ? formatTime(currentTime) : null;
  const dateStr = currentTime ? formatDate(currentTime) : null;
  const timeEmoji = currentTime ? getTimeOfDayEmoji(currentTime.getHours()) : "🕐";

  return (
    <header 
      className={`flex-shrink-0 flex items-center justify-between px-3 py-2.5 md:px-6 z-20 border-b backdrop-blur-md transition-colors duration-300 ${
        isNight 
          ? "bg-[#1c2541]/75 border-slate-700/60 text-slate-100 shadow-md" 
          : "bg-white/75 border-slate-200/70 text-slate-800 shadow-xs"
      }`}
    >
      {/* Left section: Sidebar toggle & Saki identity */}
      <div className="flex items-center gap-3">
        <button
          suppressHydrationWarning
          onClick={onToggleSidebar}
          className={`p-2 rounded-xl border transition ${
            isNight 
              ? "bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700" 
              : "bg-white/80 border-slate-200 text-slate-600 hover:bg-slate-100"
          }`}
          title={isSidebarOpen ? "Collapse sidebar" : "Open sidebar"}
          aria-label="Toggle navigation sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <div className="flex items-center gap-2.5">
          <div className="relative flex-shrink-0">
            <div className="h-9 w-9 rounded-full overflow-hidden border-2 border-indigo-400/50 shadow-sm bg-white flex items-center justify-center">
              <img 
                src="/saki.webp" 
                alt="Saki DP" 
                className="h-full w-full object-cover scale-105"
              />
            </div>
            <div className={`absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 ${isNight ? "border-slate-900" : "border-white"} ${health.dot}`}></div>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base md:text-lg font-black bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-500 bg-clip-text text-transparent">
                Saki
              </h1>
              <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${modeBadge.color}`}>
                {modeBadge.label}
              </span>
              <div className="hidden sm:flex items-center gap-1 text-[10px] font-semibold opacity-80" title={`Connection status: ${health.label}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${health.dot}`}></span>
                <span className={health.text}>{health.label}</span>
              </div>
            </div>
            <p className="text-[10px] md:text-[11px] text-slate-500 dark:text-slate-400 font-medium truncate max-w-[200px] md:max-w-[320px]">
              {activeProject ? `Focus: ${activeProject}` : "Your Close AI Companion"} • Local & Private
            </p>
          </div>
        </div>
      </div>

      {/* Right section: Clock, Theme & Brain controls */}
      <div className="flex items-center gap-2 md:gap-3">
        
        {/* Live Clock Display */}
        {timeData && (
          <div 
            className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-2xl border transition-all duration-300 select-none ${
              isNight
                ? "bg-slate-800/60 border-slate-700/80 shadow-inner shadow-slate-900/30"
                : "bg-white/70 border-slate-200/80 shadow-inner shadow-slate-100/50"
            }`}
            title={currentTime ? currentTime.toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : ""}
          >
            {/* Time-of-day emoji */}
            <span className="text-sm" aria-hidden="true">{timeEmoji}</span>
            
            {/* Digital clock */}
            <div className="flex items-baseline gap-0">
              <span className={`text-sm font-bold tabular-nums tracking-tight ${
                isNight ? "text-slate-100" : "text-slate-800"
              }`}>
                {timeData.hours}
              </span>
              <span className={`text-sm font-bold tabular-nums transition-opacity duration-200 ${
                colonVisible ? "opacity-100" : "opacity-30"
              } ${isNight ? "text-indigo-400" : "text-indigo-600"}`}>
                :
              </span>
              <span className={`text-sm font-bold tabular-nums tracking-tight ${
                isNight ? "text-slate-100" : "text-slate-800"
              }`}>
                {timeData.minutes}
              </span>
              <span className={`text-[9px] font-extrabold ml-0.5 ${
                isNight ? "text-indigo-400/80" : "text-indigo-500/80"
              }`}>
                {timeData.ampm}
              </span>
            </div>

            {/* Separator dot */}
            <span className={`h-3 w-px ${isNight ? "bg-slate-700" : "bg-slate-300"}`}></span>
            
            {/* Date */}
            <span className={`text-[10px] font-semibold whitespace-nowrap ${
              isNight ? "text-slate-400" : "text-slate-500"
            }`}>
              {dateStr}
            </span>
          </div>
        )}

        {/* Compact clock for mobile */}
        {timeData && (
          <div className={`flex sm:hidden items-center gap-1 px-2 py-1 rounded-xl border text-xs font-bold ${
            isNight
              ? "bg-slate-800/60 border-slate-700/80 text-slate-200"
              : "bg-white/70 border-slate-200/80 text-slate-700"
          }`}>
            <span className="text-[10px]">{timeEmoji}</span>
            <span className="tabular-nums">
              {timeData.hours}
              <span className={colonVisible ? "opacity-100" : "opacity-30"}>:</span>
              {timeData.minutes}
            </span>
            <span className={`text-[8px] font-extrabold ${
              isNight ? "text-indigo-400/80" : "text-indigo-500/80"
            }`}>{timeData.ampm}</span>
          </div>
        )}

        {/* Theme Toggle */}
        <button
          suppressHydrationWarning
          onClick={onToggleTheme}
          className={`px-3 py-1.5 rounded-full border text-xs font-bold transition flex items-center gap-1.5 shadow-xs ${
            isNight 
              ? "bg-slate-800/90 border-slate-700 text-amber-300 hover:bg-slate-700" 
              : "bg-white/90 border-slate-200 text-indigo-700 hover:bg-slate-50"
          }`}
          title={isNight ? "Switch to Clear Sky" : "Switch to Night Sky"}
        >
          <span>{isNight ? "🌙" : "☀️"}</span>
          <span className="hidden md:inline">{isNight ? "Night Sky" : "Clear Sky"}</span>
        </button>

        {/* Brain Panel Toggle */}
        <button
          suppressHydrationWarning
          onClick={onToggleBrain}
          className={`px-3 py-1.5 rounded-full border text-xs font-bold transition flex items-center gap-1.5 shadow-xs ${
            isBrainOpen
              ? "bg-indigo-600 text-white border-indigo-700 shadow-indigo-500/25"
              : isNight 
                ? "bg-slate-800/90 border-slate-700 text-slate-300 hover:bg-slate-700" 
                : "bg-white/90 border-slate-200 text-slate-700 hover:bg-white"
          }`}
          title="Toggle Saki Brain Telemetry"
        >
          <span>🧠</span>
          <span className="hidden sm:inline">Brain</span>
        </button>
      </div>
    </header>
  );
}
