import { useState } from "react";
import { AppSettings } from "../lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onUpdateSettings: (newSettings: Partial<AppSettings>) => void;
}

export default function SettingsModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings
}: SettingsModalProps) {
  const [localSettings, setLocalSettings] = useState<AppSettings>(settings);

  if (!isOpen) return null;

  const isNight = localSettings.theme === "night_sky";

  const handleSave = () => {
    onUpdateSettings(localSettings);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-fade-in">
      <div 
        className={`w-full max-w-lg rounded-3xl p-6 shadow-2xl border flex flex-col max-h-[85vh] ${
          isNight 
            ? "bg-[#111827] border-slate-700 text-slate-100" 
            : "bg-white border-slate-200 text-slate-800"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
              ⚙️
            </div>
            <div>
              <h2 className="text-base font-extrabold">Saki Settings</h2>
              <p className="text-xs opacity-60">Visual environment &amp; companion parameters</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Settings Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-5 pr-1 text-xs">
          
          {/* Theme Section */}
          <div className="space-y-2">
            <label className="font-extrabold uppercase text-[10px] tracking-wider opacity-60">Visual Environment Theme</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setLocalSettings((prev) => ({ ...prev, theme: "clear_sky" }))}
                className={`p-3 rounded-2xl border flex flex-col items-center gap-1.5 transition ${
                  localSettings.theme === "clear_sky"
                    ? "border-indigo-500 bg-indigo-50/50 text-indigo-700 font-bold shadow-xs"
                    : isNight ? "border-slate-700 bg-slate-800/60 text-slate-300" : "border-slate-200 bg-slate-50 text-slate-600"
                }`}
              >
                <span className="text-2xl">☀️</span>
                <span className="text-xs">Clear Sky (Day)</span>
              </button>

              <button
                onClick={() => setLocalSettings((prev) => ({ ...prev, theme: "night_sky" }))}
                className={`p-3 rounded-2xl border flex flex-col items-center gap-1.5 transition ${
                  localSettings.theme === "night_sky"
                    ? "border-indigo-500 bg-indigo-950/60 text-indigo-300 font-bold shadow-xs"
                    : isNight ? "border-slate-700 bg-slate-800/60 text-slate-300" : "border-slate-200 bg-slate-50 text-slate-600"
                }`}
              >
                <span className="text-2xl">🌙</span>
                <span className="text-xs">Night Sky (Navy)</span>
              </button>
            </div>
          </div>

          {/* Reduced Animation Toggle */}
          <div className={`p-3.5 rounded-2xl border flex items-center justify-between ${
            isNight ? "bg-slate-800/60 border-slate-700" : "bg-slate-50 border-slate-200"
          }`}>
            <div>
              <div className="font-bold text-xs">Reduced Motion / Eco Sky</div>
              <div className="text-[10px] opacity-60">Disables drifting cloud movement and simplifies blur effects</div>
            </div>
            <input
              type="checkbox"
              checked={localSettings.reduced_animation}
              onChange={(e) => setLocalSettings((prev) => ({ ...prev, reduced_animation: e.target.checked }))}
              className="h-4 w-4 rounded text-indigo-600 focus:ring-indigo-500 cursor-pointer"
            />
          </div>

          {/* Personality Sliders */}
          <div className="space-y-3">
            <label className="font-extrabold uppercase text-[10px] tracking-wider opacity-60">Companion Modulation</label>
            
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] font-semibold">
                <span>Warmth &amp; Support</span>
                <span>{Math.round(localSettings.personality_warmth * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.3"
                max="1.0"
                step="0.05"
                value={localSettings.personality_warmth}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, personality_warmth: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer accent-indigo-600"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[11px] font-semibold">
                <span>Playfulness &amp; Wit</span>
                <span>{Math.round(localSettings.personality_playfulness * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={localSettings.personality_playfulness}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, personality_playfulness: parseFloat(e.target.value) }))}
                className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg cursor-pointer accent-indigo-600"
              />
            </div>
          </div>

          {/* Privacy & System */}
          <div className={`p-3 rounded-2xl border space-y-1.5 ${
            isNight ? "bg-slate-800/40 border-slate-700/60" : "bg-slate-50/70 border-slate-200/60"
          }`}>
            <div className="flex justify-between text-[11px]">
              <span className="opacity-70">Privacy Mode</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">Local Only (Private)</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="opacity-70">Ollama Keep-Alive</span>
              <span className="font-mono opacity-80">{localSettings.auto_keep_alive || "5m"}</span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-xs font-bold transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md transition"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}
