import { useState, useEffect } from "react";
import { SakiState } from "../lib/api";
import { SakiTheme } from "../lib/theme";

interface TopBarProps {
  theme: SakiTheme;
  onToggleTheme: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isBrainOpen: boolean;
  onToggleBrain: () => void;
  healthStatus?: "Online" | "Degraded" | "Offline";
  mode?: string;
  activeProject?: string;
  sakiState?: SakiState;
  sakiActivity?: string;
  detectedLanguage?: string | null;
  isVoiceActive?: boolean;
  onToggleVoice?: () => void;
  activeView?: "chat" | "core";
  onSelectView?: (v: "chat" | "core") => void;
}

export default function TopBar({
  theme = "night_sky",
  onToggleTheme,
  isSidebarOpen,
  onToggleSidebar,
  isBrainOpen,
  onToggleBrain,
  healthStatus = "Online",
  mode = "casual",
  activeProject,
  sakiState = "IDLE",
  sakiActivity,
  detectedLanguage,
  isVoiceActive = false,
  onToggleVoice,
  activeView = "chat",
  onSelectView,
}: TopBarProps) {
  const isNight = theme === "night_sky";

  // Live Precision Clock State
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  const [colonVisible, setColonVisible] = useState(true);

  useEffect(() => {
    const initialTimer = setTimeout(() => {
      setCurrentTime(new Date());
    }, 0);

    const tickInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    const blinkInterval = setInterval(() => {
      setColonVisible((prev) => !prev);
    }, 1000);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(tickInterval);
      clearInterval(blinkInterval);
    };
  }, []);

  const getStateBadge = (st: SakiState) => {
    switch (st) {
      case "LISTENING":
        return {
          icon: "🎙️",
          label: "LISTENING",
          color: isNight
            ? "bg-rose-950/60 text-rose-300 border-rose-500/50 state-glow-listening"
            : "bg-rose-50/90 text-rose-700 border-rose-400/60 shadow-[0_0_12px_rgba(244,63,94,0.25)]",
          dot: "bg-rose-400 animate-ping",
        };
      case "PROCESSING":
        return {
          icon: "⚙️",
          label: "PROCESSING",
          color: isNight
            ? "bg-blue-950/60 text-blue-300 border-blue-500/50 state-glow-processing"
            : "bg-sky-50/90 text-sky-800 border-sky-400/60 shadow-[0_0_12px_rgba(14,165,233,0.25)]",
          dot: "bg-sky-500 animate-pulse",
        };
      case "THINKING":
        return {
          icon: "🧠",
          label: "THINKING",
          color: isNight
            ? "bg-indigo-950/60 text-indigo-300 border-indigo-500/50 state-glow-thinking"
            : "bg-indigo-50/90 text-indigo-800 border-indigo-400/60 shadow-[0_0_12px_rgba(99,102,241,0.25)]",
          dot: "bg-indigo-500 animate-pulse",
        };
      case "SEARCHING":
        return {
          icon: "🌐",
          label: "SEARCHING",
          color: isNight
            ? "bg-cyan-950/60 text-cyan-300 border-cyan-500/50 state-glow-searching"
            : "bg-cyan-50/90 text-cyan-800 border-cyan-400/60 shadow-[0_0_12px_rgba(6,182,212,0.25)]",
          dot: "bg-cyan-500 animate-ping",
        };
      case "VISION":
        return {
          icon: "👁️",
          label: "VISION",
          color: isNight
            ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/50"
            : "bg-emerald-50/90 text-emerald-800 border-emerald-400/60 shadow-[0_0_12px_rgba(16,185,129,0.25)]",
          dot: "bg-emerald-500 animate-pulse",
        };
      case "REMEMBERING":
        return {
          icon: "💾",
          label: "RECALLING",
          color: isNight
            ? "bg-purple-950/60 text-purple-300 border-purple-500/50"
            : "bg-purple-50/90 text-purple-800 border-purple-400/60 shadow-[0_0_12px_rgba(168,85,247,0.25)]",
          dot: "bg-purple-500 animate-pulse",
        };
      case "ACTING":
        return {
          icon: "⚡",
          label: "ACTING",
          color: isNight
            ? "bg-amber-950/60 text-amber-300 border-amber-500/50"
            : "bg-amber-50/90 text-amber-800 border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.25)]",
          dot: "bg-amber-500 animate-ping",
        };
      case "SPEAKING":
        return {
          icon: "🔊",
          label: "SPEAKING",
          color: isNight
            ? "bg-amber-950/60 text-amber-300 border-amber-500/50 state-glow-speaking"
            : "bg-amber-50/90 text-amber-800 border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.35)]",
          dot: "bg-amber-500 animate-ping",
        };
      case "ERROR":
        return {
          icon: "⚠️",
          label: "ERROR",
          color: isNight
            ? "bg-red-950/70 text-red-300 border-red-500/60"
            : "bg-red-50/90 text-red-800 border-red-400/60 shadow-[0_0_12px_rgba(239,68,68,0.25)]",
          dot: "bg-red-500",
        };
      case "IDLE":
      default:
        return {
          icon: "◇",
          label: "STANDBY",
          color: isNight
            ? "bg-slate-900/60 text-cyan-300 border-cyan-500/30 state-glow-idle"
            : "bg-white/80 text-sky-800 border-sky-300/50 shadow-[0_2px_12px_rgba(14,165,233,0.15)]",
          dot: isNight ? "bg-cyan-400" : "bg-sky-500",
        };
    }
  };

  const stateBadge = getStateBadge(sakiState);

  const getLanguageLabel = (lang?: string | null) => {
    if (!lang) return null;
    const l = lang.toLowerCase();
    if (l === "te" || l === "telugu") return { code: "TE", label: "తెలుగు", color: isNight ? "bg-amber-950/70 text-amber-300 border-amber-500/40" : "bg-amber-100 text-amber-900 border-amber-300" };
    if (l === "kn" || l === "kannada") return { code: "KN", label: "ಕನ್ನಡ", color: isNight ? "bg-purple-950/70 text-purple-300 border-purple-500/40" : "bg-purple-100 text-purple-900 border-purple-300" };
    if (l.includes("te") && l.includes("en")) return { code: "TE+EN", label: "తెలుగు+EN", color: isNight ? "bg-amber-950/70 text-amber-300 border-amber-500/40" : "bg-amber-100 text-amber-900 border-amber-300" };
    if (l.includes("kn") && l.includes("en")) return { code: "KN+EN", label: "ಕನ್ನಡ+EN", color: isNight ? "bg-purple-950/70 text-purple-300 border-purple-500/40" : "bg-purple-100 text-purple-900 border-purple-300" };
    return { code: "EN", label: "English", color: isNight ? "bg-slate-900/60 text-cyan-300 border-cyan-500/30" : "bg-sky-100 text-sky-800 border-sky-300" };
  };

  const langBadge = getLanguageLabel(detectedLanguage);

  // Digital clock format
  const formatTime = (date: Date) => {
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    const seconds = date.getSeconds().toString().padStart(2, "0");
    return { hours, minutes, seconds };
  };

  const timeData = currentTime ? formatTime(currentTime) : null;

  return (
    <header className="flex-shrink-0 flex items-center justify-between px-3.5 py-2.5 md:px-6 z-20 hud-panel border-b select-none transition-colors duration-500">
      {/* Left section: Sidebar toggle & Workstation Breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          suppressHydrationWarning
          onClick={onToggleSidebar}
          className={`p-2 rounded-lg border text-xs flex items-center justify-center transition ${
            isNight
              ? "border-cyan-500/20 bg-slate-900/60 text-cyan-400 hover:text-white hover:bg-slate-800/80 hover:border-cyan-400/50"
              : "border-sky-300/60 bg-white/70 text-sky-700 hover:text-sky-950 hover:bg-white hover:border-sky-400"
          }`}
          title={isSidebarOpen ? "Collapse Navigation (Ctrl+\\)" : "Expand Navigation (Ctrl+\\)"}
          aria-label="Toggle navigation"
        >
          <span className="text-sm">≡</span>
        </button>

        <div className="flex items-center gap-2">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="hud-label font-bold text-[9px]">SYS // ARCHITECTURE</span>
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-500 shadow-[0_0_6px_#0284c7]"}`} />
            </div>
            <div className={`text-[11px] font-mono truncate max-w-[130px] md:max-w-[200px] font-semibold ${isNight ? "text-slate-300" : "text-slate-700"}`}>
              {activeProject ? `WORKSPACE // ${activeProject}` : "DEFAULT // ACTIVE_CORE"}
            </div>
          </div>
        </div>

        {/* View Switcher: Chat vs Saki Core */}
        {onSelectView && (
          <div className={`hidden sm:flex items-center gap-1 rounded-xl p-0.5 border ${
            isNight 
              ? "bg-slate-950/80 border-cyan-500/30 shadow-[0_0_12px_rgba(56,189,248,0.15)]" 
              : "bg-white/80 border-sky-300/70 shadow-[0_2px_10px_rgba(14,165,233,0.12)]"
          }`}>
            <button
              type="button"
              onClick={() => onSelectView("chat")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-bold transition flex items-center gap-1.5 ${
                activeView === "chat"
                  ? isNight
                    ? "bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(56,189,248,0.25)]"
                    : "bg-sky-500 text-white shadow-xs"
                  : isNight
                    ? "text-slate-400 hover:text-slate-200"
                    : "text-slate-600 hover:text-slate-900"
              }`}
              title="Switch to Full Chat Workspace"
            >
              <span>💬</span>
              <span>Chat</span>
            </button>
            <button
              type="button"
              onClick={() => onSelectView("core")}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-bold transition flex items-center gap-1.5 ${
                activeView === "core"
                  ? isNight
                    ? "bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(56,189,248,0.25)]"
                    : "bg-sky-500 text-white shadow-xs"
                  : isNight
                    ? "text-slate-400 hover:text-cyan-300"
                    : "text-slate-600 hover:text-sky-800"
              }`}
              title="Switch to Dedicated Saki Core View"
            >
              <span>⚛️</span>
              <span>Saki Core</span>
            </button>
          </div>
        )}
      </div>

      {/* Center section: Dynamic Luminous Saki State Pill + Language Badge */}
      <div className="flex items-center gap-2">
        <div 
          className={`flex items-center gap-2 px-3 py-1 rounded-full border transition-all duration-300 ${stateBadge.color}`}
          title={sakiActivity || `Saki Core is currently ${sakiState}`}
        >
          <span className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${stateBadge.dot}`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${stateBadge.dot.replace('animate-ping', '').replace('animate-pulse', '')}`} />
          </span>
          <span className="font-mono text-[10px] font-extrabold tracking-wider">
            {stateBadge.label}
          </span>
          {sakiActivity && (
            <span className={`hidden md:inline-block max-w-[160px] truncate text-[9px] font-mono opacity-80 border-l pl-2 ${isNight ? "border-white/20 text-slate-300" : "border-slate-400/30 text-slate-700 font-medium"}`}>
              {sakiActivity}
            </span>
          )}
        </div>

        {/* Language Badge */}
        {langBadge && (
          <div
            className={`hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full border font-mono text-[10px] font-bold shadow-xs transition-all ${langBadge.color}`}
            title={`Active Spoken Language: ${langBadge.label}`}
          >
            <span>🌐</span>
            <span>{langBadge.label}</span>
          </div>
        )}

        {/* Conversation Mode Badge */}
        {mode && (
          <div
            className={`hidden lg:flex items-center gap-1 px-2.5 py-1 rounded-full border font-mono text-[10px] font-bold tracking-wider shadow-xs uppercase ${
              mode === "support"
                ? isNight ? "bg-rose-950/70 text-rose-300 border-rose-500/40" : "bg-rose-100 text-rose-800 border-rose-300"
                : mode === "builder"
                ? isNight ? "bg-emerald-950/70 text-emerald-300 border-emerald-500/40" : "bg-emerald-100 text-emerald-800 border-emerald-300"
                : mode === "thinking"
                ? isNight ? "bg-yellow-950/70 text-yellow-300 border-yellow-500/40" : "bg-yellow-100 text-yellow-800 border-yellow-300"
                : mode === "vision"
                ? isNight ? "bg-purple-950/70 text-purple-300 border-purple-500/40" : "bg-purple-100 text-purple-800 border-purple-300"
                : isNight ? "bg-slate-900/60 text-slate-300 border-slate-700/50" : "bg-slate-100 text-slate-700 border-slate-300"
            }`}
            title={`Active Conversational Mode: ${mode}`}
          >
            <span>{mode === "support" ? "❤️" : mode === "builder" ? "⚡" : mode === "thinking" ? "🧠" : mode === "vision" ? "👁️" : "💬"}</span>
            <span>{mode}</span>
          </div>
        )}

        {/* Voice Toggle Button */}
        {onToggleVoice && (
          <button
            type="button"
            onClick={onToggleVoice}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border font-mono text-[10px] font-bold transition-all ${
              isVoiceActive
                ? isNight ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.3)]" : "bg-emerald-100 text-emerald-800 border-emerald-300 shadow-sm"
                : isNight ? "bg-slate-900/50 text-slate-400 border-slate-800 hover:text-slate-200" : "bg-slate-100 text-slate-600 border-slate-300 hover:text-slate-800"
            }`}
            title={isVoiceActive ? "Voice is Armed / Active" : "Voice is Inactive (Click to Activate)"}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isVoiceActive ? "bg-emerald-400 animate-ping" : "bg-slate-500"}`} />
            <span>{isVoiceActive ? "VOICE ON" : "VOICE OFF"}</span>
          </button>
        )}
      </div>

      {/* Right section: Precision Digital Clock, Theme Switcher & Brain HUD Toggle */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Health status indicator */}
        <div
          className={`hidden xl:flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] border ${
            healthStatus === "Online"
              ? isNight ? "border-emerald-500/30 text-emerald-400 bg-emerald-950/40" : "border-emerald-300 text-emerald-700 bg-emerald-50"
              : healthStatus === "Degraded"
              ? isNight ? "border-amber-500/30 text-amber-400 bg-amber-950/40" : "border-amber-300 text-amber-700 bg-amber-50"
              : isNight ? "border-rose-500/30 text-rose-400 bg-rose-950/40" : "border-rose-300 text-rose-700 bg-rose-50"
          }`}
          title={`Backend Brain Status: ${healthStatus}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${healthStatus === "Online" ? "bg-emerald-400" : healthStatus === "Degraded" ? "bg-amber-400" : "bg-rose-400"}`} />
          <span>{healthStatus}</span>
        </div>
        {/* Precision Digital Clock */}
        {timeData && (
          <div 
            className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-mono text-xs ${
              isNight
                ? "border-cyan-500/20 bg-slate-950/60 text-slate-300"
                : "border-sky-300/60 bg-white/70 text-slate-700 shadow-sm"
            }`}
            title="Local System Time"
          >
            <span className={`text-[10px] font-bold ${isNight ? "text-cyan-400" : "text-sky-600"}`}>TIME //</span>
            <span className={`font-bold tabular-nums ${isNight ? "text-slate-100" : "text-slate-900"}`}>{timeData.hours}</span>
            <span className={`font-bold transition-opacity ${colonVisible ? (isNight ? "opacity-100 text-cyan-400" : "opacity-100 text-sky-600") : "opacity-30 text-slate-400"}`}>:</span>
            <span className={`font-bold tabular-nums ${isNight ? "text-slate-100" : "text-slate-900"}`}>{timeData.minutes}</span>
            <span className={`font-bold transition-opacity ${colonVisible ? (isNight ? "opacity-100 text-cyan-400" : "opacity-100 text-sky-600") : "opacity-30 text-slate-400"}`}>:</span>
            <span className={`text-[10px] font-bold tabular-nums ${isNight ? "text-cyan-300" : "text-sky-700"}`}>{timeData.seconds}</span>
          </div>
        )}

        {/* ☀️ / 🌙 1-Click Environment Theme Toggle (Sprint 13) */}
        <button
          suppressHydrationWarning
          onClick={onToggleTheme}
          className={`px-2.5 py-1.5 rounded-xl border text-xs font-mono font-bold transition-all duration-300 flex items-center gap-1.5 shadow-sm ${
            isNight
              ? "bg-slate-900/70 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/60 hover:border-cyan-400 hover:text-white"
              : "bg-white/80 border-sky-400 text-sky-800 hover:bg-sky-50 hover:text-sky-950 shadow-[0_2px_8px_rgba(14,165,233,0.2)]"
          }`}
          title={isNight ? "Switch to Clear Sky Environment (☀️)" : "Switch to Night Sky Environment (🌙)"}
          aria-label="Toggle environment theme"
        >
          <span className="text-sm">{isNight ? "🌙" : "☀️"}</span>
          <span className="hidden md:inline tracking-wider text-[10px]">
            {isNight ? "NIGHT" : "CLEAR SKY"}
          </span>
        </button>

        {/* Brain Telemetry Panel Toggle */}
        <button
          suppressHydrationWarning
          onClick={onToggleBrain}
          className={`px-3 py-1.5 rounded-xl border text-xs font-bold font-mono transition-all duration-200 flex items-center gap-1.5 shadow-md ${
            isBrainOpen
              ? isNight
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_15px_rgba(56,189,248,0.3)]"
                : "bg-sky-500/20 text-sky-800 border-sky-500 shadow-[0_0_15px_rgba(14,165,233,0.25)]"
              : isNight
              ? "bg-slate-900/70 border-cyan-500/20 text-slate-300 hover:text-white hover:border-cyan-400/50 hover:bg-slate-800/80"
              : "bg-white/70 border-sky-300/60 text-slate-700 hover:text-slate-900 hover:border-sky-400 hover:bg-white"
          }`}
          title="Toggle Saki Brain Telemetry (Ctrl+B)"
        >
          <span className="text-xs">🧠</span>
          <span className="hidden sm:inline tracking-wider">BRAIN HUD</span>
          <span className={`text-[9px] ml-0.5 border px-1 rounded hidden md:inline ${isNight ? "border-white/20 opacity-60 text-slate-300" : "border-slate-300 text-slate-600"}`}>
            ⌘B
          </span>
        </button>
      </div>
    </header>
  );
}
