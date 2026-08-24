import { BrainStatusData, SakiState } from "../lib/api";
import { SakiTheme } from "../lib/theme";

interface BrainPanelProps {
  isOpen: boolean;
  onClose: () => void;
  brainStatus: BrainStatusData | null;
  theme?: SakiTheme;
  sakiState?: SakiState;
  sakiActivity?: string;
  detectedLanguage?: string | null;
  voiceTelemetry?: {
    volume?: number;
    speechActive?: boolean;
    ttsLatencyMs?: number;
    sttLatencyMs?: number;
    interruptionsCount?: number;
  };
}

export default function BrainPanel({
  isOpen,
  onClose,
  brainStatus,
  theme = "night_sky",
  sakiState = "IDLE",
  sakiActivity,
  detectedLanguage,
  voiceTelemetry,
}: BrainPanelProps) {
  if (!isOpen) return null;

  const isNight = theme === "night_sky";
  const awareness = brainStatus?.awareness;
  const emotion = awareness?.emotional_state;
  const social = awareness?.social_energy;

  const getModeBadge = (m: string) => {
    switch (m) {
      case "builder": 
        return { label: "BUILDER", color: isNight ? "text-emerald-400 bg-emerald-950/60 border-emerald-500/40" : "text-emerald-800 bg-emerald-100/90 border-emerald-400" };
      case "support": 
        return { label: "SUPPORT", color: isNight ? "text-rose-400 bg-rose-950/60 border-rose-500/40" : "text-rose-800 bg-rose-100/90 border-rose-400" };
      case "thinking": 
        return { label: "THINKING", color: isNight ? "text-indigo-400 bg-indigo-950/60 border-indigo-500/40" : "text-indigo-800 bg-indigo-100/90 border-indigo-400" };
      case "vision": 
        return { label: "VISION", color: isNight ? "text-cyan-400 bg-cyan-950/60 border-cyan-500/40" : "text-sky-800 bg-sky-100/90 border-sky-400" };
      default: 
        return { label: "CASUAL", color: isNight ? "text-amber-400 bg-amber-950/60 border-amber-500/40" : "text-amber-800 bg-amber-100/90 border-amber-400" };
    }
  };

  const modeBadge = getModeBadge(brainStatus?.mode || awareness?.conversation_mode || "casual");

  const subcardClass = isNight
    ? "bg-slate-950/60 border-cyan-500/15"
    : "bg-white/80 border-sky-200/80 shadow-xs";

  return (
    <aside
      className={`fixed lg:static inset-y-0 right-0 w-[330px] md:w-[360px] flex-shrink-0 flex flex-col h-full z-40 animate-slide-left border-l hud-panel overflow-y-auto p-4 space-y-3.5 select-none transition-colors duration-500 ${
        isNight ? "text-slate-200 border-cyan-500/15" : "text-slate-800 border-sky-300/40"
      }`}
    >
      {/* Panel Top Header */}
      <div className={`flex items-center justify-between border-b pb-3 ${isNight ? "border-cyan-500/15" : "border-sky-200/60"}`}>
        <div className="flex items-center gap-2.5">
          <div className={`h-7 w-7 rounded-lg border flex items-center justify-center font-mono text-xs shadow-sm ${
            isNight ? "bg-cyan-950/80 border-cyan-500/40 text-cyan-300" : "bg-sky-100 border-sky-400 text-sky-700"
          }`}>
            🧠
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="hud-label font-bold text-[10px]">BRAIN // TELEMETRY</span>
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-500 shadow-[0_0_6px_#0284c7]"}`} />
            </div>
            <p className={`text-[10px] font-mono ${isNight ? "text-slate-400" : "text-slate-600"}`}>Live Neural &amp; Runtime Matrix</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className={`p-1 rounded-lg transition text-xs font-mono ${
            isNight ? "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60" : "text-slate-500 hover:text-sky-900 hover:bg-sky-100/70"
          }`}
          title="Close Brain Panel (Esc)"
        >
          ✕
        </button>
      </div>

      {/* 1. Core State & Activity Card */}
      <div className="p-3 rounded-xl hud-card hud-corner-bracket space-y-2">
        <div className="flex justify-between items-center">
          <span className="hud-label">Saki Core State</span>
          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border ${
            isNight ? "bg-cyan-950/70 text-cyan-300 border-cyan-500/40" : "bg-sky-100 text-sky-800 border-sky-300"
          }`}>
            {sakiState}
          </span>
        </div>
        <div className={`p-2 rounded-lg border space-y-1 ${subcardClass}`}>
          <div className="flex justify-between text-[10px] font-mono">
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>Activity:</span>
            <span className={`font-semibold truncate max-w-[170px] ${isNight ? "text-cyan-200" : "text-sky-900"}`}>
              {sakiActivity || "Awaiting Operator Input"}
            </span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>Engine:</span>
            <span className={`font-semibold ${isNight ? "text-emerald-400" : "text-emerald-700"}`}>
              WebGL 3D Plasma Core
            </span>
          </div>
        </div>
      </div>

      {/* 2. Model & Cognitive Mode Card */}
      <div className="p-3 rounded-xl hud-card space-y-2">
        <div className="flex justify-between items-center">
          <span className="hud-label">Cognitive Mode</span>
          <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${modeBadge.color}`}>
            {modeBadge.label}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className={`p-2 rounded-lg border ${subcardClass}`}>
            <div className="text-[8px] hud-label">Active Model</div>
            <div className={`font-bold text-[11px] truncate mt-0.5 ${isNight ? "text-cyan-300" : "text-sky-900"}`}>
              {brainStatus?.model || "phi3:latest"}
            </div>
          </div>
          <div className={`p-2 rounded-lg border ${subcardClass}`}>
            <div className="text-[8px] hud-label">Model Status</div>
            <div className={`font-bold text-[11px] truncate mt-0.5 ${isNight ? "text-emerald-400" : "text-emerald-700"}`}>
              {brainStatus?.state || "STANDBY"}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Voice & Acoustic Engine Telemetry */}
      <div className="p-3 rounded-xl hud-card space-y-2">
        <div className="flex justify-between items-center">
          <span className="hud-label">Voice & Acoustic Stream</span>
          <span className={`text-[9px] font-mono font-bold ${isNight ? "text-cyan-400" : "text-sky-700"}`}>KOKORO // WHISPER</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className={`p-2 rounded-lg border ${subcardClass}`}>
            <div className="text-[8px] hud-label">Active Language</div>
            <div className={`font-bold text-[11px] mt-0.5 ${
              detectedLanguage === "te" ? "text-amber-400" :
              detectedLanguage === "kn" ? "text-purple-400" :
              detectedLanguage?.includes("+") ? "text-emerald-400" :
              isNight ? "text-cyan-300" : "text-sky-800"
            }`}>
              {detectedLanguage === "te" ? "తెలుగు (TE)" :
               detectedLanguage === "kn" ? "ಕನ್ನಡ (KN)" :
               detectedLanguage === "te+en" ? "తెలుగు+EN" :
               detectedLanguage === "kn+en" ? "ಕನ್ನಡ+EN" :
               "English (EN)"}
            </div>
          </div>
          <div className={`p-2 rounded-lg border ${subcardClass}`}>
            <div className="text-[8px] hud-label">TTS Voice</div>
            <div className={`font-bold text-[11px] mt-0.5 ${
              detectedLanguage === "te" ? "text-amber-300" :
              detectedLanguage === "kn" ? "text-purple-300" :
              isNight ? "text-amber-300" : "text-amber-700"
            }`}>
              {detectedLanguage === "te" ? "te_saki" : detectedLanguage === "kn" ? "kn_saki" : "af_heart"}
            </div>
          </div>
          <div className={`p-2 rounded-lg border ${subcardClass}`}>
            <div className="text-[8px] hud-label">STT Multilingual</div>
            <div className={`font-bold text-[11px] mt-0.5 ${isNight ? "text-cyan-300" : "text-sky-800"}`}>whisper-tiny</div>
          </div>
          <div className={`p-2 rounded-lg border ${subcardClass}`}>
            <div className="text-[8px] hud-label">Barge-In Latency</div>
            <div className={`font-bold text-[11px] mt-0.5 ${isNight ? "text-rose-400" : "text-rose-700"}`}>
              {voiceTelemetry?.sttLatencyMs ? `${Math.round(voiceTelemetry.sttLatencyMs)} ms` : "< 30ms"}
            </div>
          </div>
        </div>
      </div>

      {/* 4. Hardware & Resource Matrix (Sprint 20) */}
      <div className="p-3 rounded-xl hud-card space-y-2">
        <div className="flex justify-between items-center">
          <span className="hud-label">Hardware &amp; Execution Matrix</span>
          <span className={`text-[9px] font-mono font-bold ${isNight ? "text-cyan-400" : "text-sky-700"}`}>LOCAL RESOURCE RT</span>
        </div>
        <div className="space-y-1.5 font-mono text-[10px]">
          <div className={`p-2 rounded-lg border flex justify-between items-center ${subcardClass}`}>
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>Host RAM:</span>
            <span className={`font-bold truncate max-w-[170px] ${isNight ? "text-cyan-300" : "text-sky-800"}`}>
              {brainStatus?.ram_usage || "Unavailable"}
            </span>
          </div>
          <div className={`p-2 rounded-lg border flex justify-between items-center ${subcardClass}`}>
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>Compute / GPU:</span>
            <span className={`font-bold truncate max-w-[170px] ${isNight ? "text-slate-200" : "text-slate-900"}`}>
              {brainStatus?.gpu_name || "CPU-Only / Shared RAM"}
            </span>
          </div>
          <div className={`p-2 rounded-lg border flex justify-between items-center ${subcardClass}`}>
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>VRAM / Alloc:</span>
            <span className={`font-bold truncate max-w-[170px] ${isNight ? "text-amber-300" : "text-amber-800"}`}>
              {brainStatus?.vram_usage || "Shared Memory"}
            </span>
          </div>
          <div className={`p-2 rounded-lg border flex justify-between items-center ${subcardClass}`}>
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>Resident Models:</span>
            <span className={`font-bold ${isNight ? "text-emerald-400" : "text-emerald-700"}`}>
              {brainStatus?.loaded_models_count ?? 1} active/idle
            </span>
          </div>
          <div className={`p-2 rounded-lg border flex justify-between items-center ${subcardClass}`}>
            <span className={isNight ? "text-slate-400" : "text-slate-600"}>Turn Latency &amp; Speed:</span>
            <span className={`font-bold ${isNight ? "text-purple-300" : "text-purple-700"}`}>
              {brainStatus?.latency_ms ? `${brainStatus.latency_ms.toFixed(0)}ms` : "0ms"} ({brainStatus?.tokens_per_second ? `${brainStatus.tokens_per_second.toFixed(1)} t/s` : "0.0 t/s"})
            </span>
          </div>
        </div>
      </div>

      {/* 5. Emotional & Social Energy Radar */}
      <div className="p-3 rounded-xl hud-card space-y-2">
        <div className="flex justify-between items-center">
          <span className="hud-label">Emotional Radar</span>
          <span className={`text-[9px] font-mono capitalize font-bold ${isNight ? "text-rose-400" : "text-rose-700"}`}>
            {emotion?.emotion || "attentive"} ({Math.round((emotion?.intensity ?? 0.7) * 100)}%)
          </span>
        </div>
        <div className="space-y-1.5 font-mono text-[9px]">
          <div className="space-y-0.5">
            <div className="flex justify-between">
              <span className={isNight ? "text-slate-400" : "text-slate-600"}>Warmth &amp; Resonance</span>
              <span className={isNight ? "text-cyan-300" : "text-sky-800"}>{Math.round((social?.warmth ?? 0.8) * 100)}%</span>
            </div>
            <div className="w-full h-1 bg-slate-800/40 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-cyan-500 to-sky-400 rounded-full transition-all duration-500" 
                style={{ width: `${Math.round((social?.warmth ?? 0.8) * 100)}%` }}
              />
            </div>
          </div>
          <div className="space-y-0.5">
            <div className="flex justify-between">
              <span className={isNight ? "text-slate-400" : "text-slate-600"}>Playfulness &amp; Wit</span>
              <span className={isNight ? "text-purple-300" : "text-purple-800"}>{Math.round((social?.playfulness ?? 0.6) * 100)}%</span>
            </div>
            <div className="w-full h-1 bg-slate-800/40 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-500 to-pink-400 rounded-full transition-all duration-500" 
                style={{ width: `${Math.round((social?.playfulness ?? 0.6) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
