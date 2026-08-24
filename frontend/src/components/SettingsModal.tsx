import { useState } from "react";
import { AppSettings, SakiState } from "../lib/api";
import { SakiTheme } from "../lib/theme";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onUpdateSettings: (newSettings: Partial<AppSettings>) => void;
  onPreviewState?: (state: SakiState) => void;
}

export default function SettingsModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onPreviewState
}: SettingsModalProps) {
  const [localSettings, setLocalSettings] = useState<AppSettings>(settings);

  if (!isOpen) return null;

  const isNight = (localSettings.theme ?? "night_sky") === "night_sky";

  const handleSave = () => {
    onUpdateSettings(localSettings);
    onClose();
  };

  const handleSelectTheme = (t: SakiTheme) => {
    setLocalSettings((prev) => ({ ...prev, theme: t }));
    // Also propagate immediately to give instant visual feedback
    onUpdateSettings({ theme: t });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fade-in select-none">
      <div 
        className={`w-full max-w-lg rounded-2xl p-5 shadow-2xl border hud-panel-glow flex flex-col max-h-[88vh] hud-corner-bracket transition-colors duration-300 ${
          isNight ? "text-slate-100" : "text-slate-900"
        }`}
        data-theme={localSettings.theme}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3.5 border-b border-cyan-500/20">
          <div className="flex items-center gap-2.5">
            <div className={`h-8 w-8 rounded-lg border flex items-center justify-center font-bold text-sm shadow-sm ${
              isNight ? "bg-cyan-950/80 border-cyan-500/40 text-cyan-300" : "bg-sky-100 border-sky-400 text-sky-700"
            }`}>
              ⚙️
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="hud-label font-bold text-[10px]">SYSTEM // CONFIG</span>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#38bdf8]" />
              </div>
              <p className={`text-[10px] font-mono ${isNight ? "text-slate-400" : "text-slate-600"}`}>
                Workstation &amp; Atmosphere Parameters
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-1 rounded-lg font-mono transition text-xs ${
              isNight ? "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60" : "text-slate-600 hover:text-sky-900 hover:bg-slate-200/70"
            }`}
          >
            ✕
          </button>
        </div>

        {/* Settings Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1 text-xs">
          
          {/* 1. Visual Environment Theme Selector (Sprint 13) */}
          <div className="p-3.5 rounded-xl hud-card border space-y-2.5">
            <div className="flex justify-between items-center">
              <span className="hud-label">Atmospheric Environment</span>
              <span className={`font-mono font-bold text-[10px] uppercase ${isNight ? "text-cyan-300" : "text-sky-700"}`}>
                {localSettings.theme === "clear_sky" ? "☀️ Clear Sky" : "🌙 Night Sky"}
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-2.5 pt-1">
              {/* Clear Sky Option */}
              <button
                type="button"
                onClick={() => handleSelectTheme("clear_sky")}
                className={`p-3 rounded-xl border text-left transition-all duration-200 flex flex-col gap-1.5 ${
                  localSettings.theme === "clear_sky"
                    ? "border-sky-500 bg-sky-500/15 ring-2 ring-sky-400/40 shadow-[0_0_15px_rgba(14,165,233,0.25)]"
                    : isNight
                    ? "border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-800/60"
                    : "border-slate-300 bg-white/70 hover:border-sky-400 hover:bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-base">☀️</span>
                  {localSettings.theme === "clear_sky" && (
                    <span className="text-[9px] font-mono font-bold text-sky-600 bg-sky-100 px-1.5 py-0.5 rounded border border-sky-300">
                      ACTIVE
                    </span>
                  )}
                </div>
                <div>
                  <div className={`font-bold font-mono text-[11px] ${isNight ? "text-slate-200" : "text-slate-900"}`}>
                    Clear Sky
                  </div>
                  <div className={`text-[9px] leading-tight line-clamp-2 ${isNight ? "text-slate-400" : "text-slate-600"}`}>
                    Daytime atmosphere with procedural drifting clouds &amp; light glass UI.
                  </div>
                </div>
              </button>

              {/* Night Sky Option */}
              <button
                type="button"
                onClick={() => handleSelectTheme("night_sky")}
                className={`p-3 rounded-xl border text-left transition-all duration-200 flex flex-col gap-1.5 ${
                  localSettings.theme === "night_sky"
                    ? "border-cyan-400 bg-cyan-950/40 ring-2 ring-cyan-400/40 shadow-[0_0_15px_rgba(56,189,248,0.25)]"
                    : isNight
                    ? "border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-800/60"
                    : "border-slate-300 bg-white/70 hover:border-sky-400 hover:bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-base">🌙</span>
                  {localSettings.theme === "night_sky" && (
                    <span className="text-[9px] font-mono font-bold text-cyan-300 bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-500/40">
                      ACTIVE
                    </span>
                  )}
                </div>
                <div>
                  <div className={`font-bold font-mono text-[11px] ${isNight ? "text-slate-200" : "text-slate-900"}`}>
                    Night Sky
                  </div>
                  <div className={`text-[9px] leading-tight line-clamp-2 ${isNight ? "text-slate-400" : "text-slate-600"}`}>
                    Cinematic dark cosmic cybernetic environment with glowing reticles.
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* 2. Audio Sensitivity & Voice Engine */}
          <div className="p-3.5 rounded-xl hud-card border space-y-2.5">
            <div className="flex justify-between items-center">
              <span className="hud-label">Audio-Reactive Core Sensitivity</span>
              <span className={`font-mono font-bold ${isNight ? "text-cyan-300" : "text-sky-700"}`}>
                {Math.round((localSettings.audio_sensitivity ?? 1.0) * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.2"
              max="2.5"
              step="0.05"
              value={localSettings.audio_sensitivity ?? 1.0}
              onChange={(e) => setLocalSettings((prev) => ({ ...prev, audio_sensitivity: parseFloat(e.target.value) }))}
              className="w-full h-1.5 rounded-lg cursor-pointer accent-cyan-500 bg-slate-700/50"
            />
            <div className={`flex justify-between text-[9px] font-mono ${isNight ? "text-slate-400" : "text-slate-500"}`}>
              <span>0.2x (Subtle)</span>
              <span>1.0x (Standard)</span>
              <span>2.5x (Dynamic)</span>
            </div>
          </div>

          {/* 3. Saki Core Engine Visual Settings */}
          <div className="p-3.5 rounded-xl hud-card border space-y-3">
            <span className="hud-label">Saki Core Visual Engine</span>
            
            {/* Quality Preset */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className={isNight ? "text-slate-300" : "text-slate-700"}>Rendering Quality</span>
                <span className={`font-bold uppercase ${isNight ? "text-cyan-400" : "text-sky-700"}`}>
                  {localSettings.core_quality || "auto"}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {(["low", "medium", "auto", "high", "ultra"] as const).map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setLocalSettings((prev) => ({ ...prev, core_quality: q }))}
                    className={`py-1 px-1 rounded-lg border text-[9px] font-mono font-bold uppercase transition ${
                      (localSettings.core_quality || "auto") === q
                        ? isNight
                          ? "border-cyan-400 bg-cyan-500/25 text-cyan-200 shadow-[0_0_10px_rgba(56,189,248,0.2)]"
                          : "border-sky-500 bg-sky-500/20 text-sky-800 shadow-[0_0_10px_rgba(14,165,233,0.2)]"
                        : isNight
                        ? "border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                        : "border-slate-300 bg-white/70 text-slate-600 hover:text-slate-900 hover:border-sky-400"
                    }`}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* Core Opacity Slider */}
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] font-mono">
                <span className={isNight ? "text-slate-300" : "text-slate-700"}>Core Centerstage Opacity</span>
                <span className={`font-bold ${isNight ? "text-cyan-300" : "text-sky-700"}`}>
                  {Math.round((localSettings.core_opacity ?? 0.85) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.2"
                max="1.0"
                step="0.05"
                value={localSettings.core_opacity ?? 0.85}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, core_opacity: parseFloat(e.target.value) }))}
                className="w-full h-1.5 rounded-lg cursor-pointer accent-cyan-500 bg-slate-700/50"
              />
            </div>

            {/* HUD Telemetry Toggle */}
            <div className="flex items-center justify-between pt-1">
              <span className={`text-[11px] font-mono ${isNight ? "text-slate-300" : "text-slate-700"}`}>
                Show HUD Telemetry Glyphs
              </span>
              <input
                type="checkbox"
                checked={localSettings.core_show_hud !== false}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, core_show_hud: e.target.checked }))}
                className="h-4 w-4 rounded accent-cyan-500 cursor-pointer"
              />
            </div>

            {/* Reduced Animation Toggle */}
            <div className="flex items-center justify-between pt-1 border-t border-cyan-500/10">
              <span className={`text-[11px] font-mono ${isNight ? "text-slate-300" : "text-slate-700"}`}>
                Reduced Motion Mode
              </span>
              <input
                type="checkbox"
                checked={localSettings.reduced_animation || false}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, reduced_animation: e.target.checked }))}
                className="h-4 w-4 rounded accent-cyan-500 cursor-pointer"
              />
            </div>

            {/* Live State Transition Tester */}
            {onPreviewState && (
              <div className="space-y-1.5 pt-2 border-t border-cyan-500/15">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className={isNight ? "text-slate-300" : "text-slate-700"}>Core State Transition Test</span>
                  <span className={`text-[9px] font-bold ${isNight ? "text-cyan-400" : "text-sky-600"}`}>10 STATES</span>
                </div>
                <div className="grid grid-cols-5 gap-1 text-[10px] font-mono">
                  {(["IDLE", "LISTENING", "PROCESSING", "THINKING", "SEARCHING", "VISION", "REMEMBERING", "ACTING", "SPEAKING", "ERROR"] as const).map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => onPreviewState(st)}
                      className={`py-1 px-1 rounded-md border text-[8px] font-bold transition truncate ${
                        isNight
                          ? "border-cyan-500/20 bg-slate-900/60 hover:bg-cyan-950/60 hover:border-cyan-400 text-slate-300 hover:text-cyan-200"
                          : "border-sky-300 bg-white/70 hover:bg-sky-100 hover:border-sky-400 text-slate-700 hover:text-sky-950"
                      }`}
                      title={`Trigger ${st} State`}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 4. Personality Modulation */}
          <div className="p-3.5 rounded-xl hud-card border space-y-2.5">
            <span className="hud-label">Companion Modulation</span>
            <div className="space-y-1 font-mono">
              <div className="flex justify-between text-[11px]">
                <span className={isNight ? "text-slate-300" : "text-slate-700"}>Warmth &amp; Empathy</span>
                <span className={`font-bold ${isNight ? "text-cyan-300" : "text-sky-700"}`}>
                  {Math.round((localSettings.personality_warmth ?? 0.85) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.3"
                max="1.0"
                step="0.05"
                value={localSettings.personality_warmth ?? 0.85}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, personality_warmth: parseFloat(e.target.value) }))}
                className="w-full h-1.5 rounded-lg cursor-pointer accent-cyan-500 bg-slate-700/50"
              />
            </div>
            <div className="space-y-1 font-mono">
              <div className="flex justify-between text-[11px]">
                <span className={isNight ? "text-slate-300" : "text-slate-700"}>Playfulness &amp; Wit</span>
                <span className={`font-bold ${isNight ? "text-purple-300" : "text-purple-700"}`}>
                  {Math.round((localSettings.personality_playfulness ?? 0.60) * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={localSettings.personality_playfulness ?? 0.60}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, personality_playfulness: parseFloat(e.target.value) }))}
                className="w-full h-1.5 rounded-lg cursor-pointer accent-purple-500 bg-slate-700/50"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-cyan-500/20 flex justify-end gap-2">
          <button
            onClick={onClose}
            className={`px-3.5 py-1.5 rounded-xl border font-mono text-xs font-bold transition ${
              isNight ? "bg-slate-900 border-slate-700 hover:bg-slate-800 text-slate-300" : "bg-slate-100 border-slate-300 hover:bg-slate-200 text-slate-700"
            }`}
          >
            CANCEL
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-mono text-xs font-bold shadow-[0_0_15px_rgba(56,189,248,0.3)] transition"
          >
            APPLY CONFIG
          </button>
        </div>
      </div>
    </div>
  );
}
