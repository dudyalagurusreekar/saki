import { BrainStatusData } from "../lib/api";

interface BrainPanelProps {
  isOpen: boolean;
  onClose: () => void;
  brainStatus: BrainStatusData | null;
  theme?: "clear_sky" | "night_sky";
}

export default function BrainPanel({
  isOpen,
  onClose,
  brainStatus,
  theme = "clear_sky"
}: BrainPanelProps) {
  if (!isOpen) return null;

  const isNight = theme === "night_sky";
  const awareness = brainStatus?.awareness;
  const cognitive = brainStatus?.cognitive_state;
  const emotion = awareness?.emotional_state;
  const social = awareness?.social_energy;

  const getModeLabel = (m: string) => {
    switch (m) {
      case "builder": return { label: "💻 Builder Mode", color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30" };
      case "support": return { label: "❤️ Support Mode", color: "text-rose-500 bg-rose-500/10 border-rose-500/30" };
      case "thinking": return { label: "🧠 Thinking Mode", color: "text-indigo-500 bg-indigo-500/10 border-indigo-500/30" };
      case "vision": return { label: "👁️ Vision Mode", color: "text-cyan-500 bg-cyan-500/10 border-cyan-500/30" };
      default: return { label: "⚡ Casual Mode", color: "text-amber-500 bg-amber-500/10 border-amber-500/30" };
    }
  };

  const modeBadge = getModeLabel(brainStatus?.mode || awareness?.conversation_mode || "casual");

  return (
    <aside
      className={`fixed lg:static inset-y-0 right-0 w-[340px] md:w-[380px] flex-shrink-0 flex flex-col h-full z-40 animate-slide-left border-l overflow-y-auto p-4 md:p-5 space-y-4 shadow-xl lg:shadow-none ${
        isNight 
          ? "bg-[#111827]/95 border-slate-800 text-slate-100 backdrop-blur-2xl" 
          : "bg-white/90 border-slate-200 text-slate-800 backdrop-blur-xl"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-3 border-slate-200/70 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-black text-sm shadow-md">
            🧠
          </div>
          <div>
            <h2 className="font-extrabold text-sm leading-tight">Saki Brain & Telemetry</h2>
            <p className="text-[10px] opacity-60 font-semibold">Live System & Cognitive Metrics</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-md transition text-xs"
          title="Close Brain Panel"
        >
          ✕
        </button>
      </div>

      {/* 1. Mode Card */}
      <div className={`p-3 rounded-2xl border ${isNight ? "bg-slate-900/80 border-slate-800" : "bg-white border-slate-200/80 shadow-2xs"}`}>
        <div className="flex justify-between items-center mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-60">Cognitive Mode</span>
          <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${modeBadge.color}`}>
            {modeBadge.label}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className={`p-2 rounded-xl border ${isNight ? "bg-slate-800/60 border-slate-700/50" : "bg-slate-50 border-slate-100"}`}>
            <div className="text-[9px] opacity-60 font-bold uppercase">Task</div>
            <div className="font-bold truncate capitalize text-[11px] mt-0.5">
              {cognitive?.conversation?.task || awareness?.current_activity || "casual_chat"}
            </div>
          </div>
          <div className={`p-2 rounded-xl border ${isNight ? "bg-slate-800/60 border-slate-700/50" : "bg-slate-50 border-slate-100"}`}>
            <div className="text-[9px] opacity-60 font-bold uppercase">Stage</div>
            <div className="font-bold truncate capitalize text-[11px] mt-0.5">
              {cognitive?.conversation?.stage || "exploring"}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Model Card */}
      <div className={`p-3 rounded-2xl border ${isNight ? "bg-slate-900/80 border-slate-800" : "bg-white border-slate-200/80 shadow-2xs"}`}>
        <div className="flex justify-between items-center text-xs mb-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-60">Active Model</span>
          <span className="font-mono text-[10px] bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded font-bold border border-indigo-200 dark:border-indigo-800">
            {brainStatus?.model || "phi3:latest"}
          </span>
        </div>
        <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-100 dark:border-slate-800">
          <span className="opacity-70 text-[11px]">Model State</span>
          <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
            brainStatus?.state === "ACTIVE" 
              ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400" 
              : "bg-slate-500/20 text-slate-600 dark:text-slate-400"
          }`}>
            {brainStatus?.state || "IDLE"}
          </span>
        </div>
      </div>

      {/* 3. Performance Telemetry Card */}
      <div className={`p-3.5 rounded-2xl border ${isNight ? "bg-slate-900/80 border-slate-800" : "bg-white border-slate-200/80 shadow-2xs"} space-y-2`}>
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-60">Performance Telemetry</span>
          <span className="text-[9px] font-mono opacity-50">REAL-TIME</span>
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className={`p-2 rounded-xl border ${isNight ? "bg-slate-800/60 border-slate-700/50" : "bg-slate-50 border-slate-100"}`}>
            <div className="text-[9px] opacity-60 font-bold uppercase">Latency</div>
            <div className="font-bold text-[12px] text-indigo-600 dark:text-indigo-400 mt-0.5">
              {brainStatus?.latency_ms ? `${(brainStatus.latency_ms / 1000).toFixed(2)} s` : "N/A"}
            </div>
          </div>

          <div className={`p-2 rounded-xl border ${isNight ? "bg-slate-800/60 border-slate-700/50" : "bg-slate-50 border-slate-100"}`}>
            <div className="text-[9px] opacity-60 font-bold uppercase">First Token</div>
            <div className="font-bold text-[12px] text-indigo-600 dark:text-indigo-400 mt-0.5">
              {brainStatus?.first_token_latency ? `${brainStatus.first_token_latency.toFixed(2)} s` : "N/A"}
            </div>
          </div>

          <div className={`p-2 rounded-xl border ${isNight ? "bg-slate-800/60 border-slate-700/50" : "bg-slate-50 border-slate-100"}`}>
            <div className="text-[9px] opacity-60 font-bold uppercase">Speed</div>
            <div className="font-bold text-[12px] text-emerald-600 dark:text-emerald-400 mt-0.5">
              {brainStatus?.tokens_per_second ? `${brainStatus.tokens_per_second.toFixed(1)} tok/s` : "N/A"}
            </div>
          </div>

          <div className={`p-2 rounded-xl border ${isNight ? "bg-slate-800/60 border-slate-700/50" : "bg-slate-50 border-slate-100"}`}>
            <div className="text-[9px] opacity-60 font-bold uppercase">Total Tokens</div>
            <div className="font-bold text-[12px] text-slate-700 dark:text-slate-300 mt-0.5">
              {brainStatus?.total_tokens ? brainStatus.total_tokens.toLocaleString() : "N/A"}
            </div>
          </div>
        </div>

        <div className="flex justify-between text-[10px] opacity-70 pt-1">
          <span>Input: {brainStatus?.input_tokens || 0} tok</span>
          <span>Output: {brainStatus?.output_tokens || 0} tok</span>
        </div>
      </div>

      {/* 4. Resources Card */}
      <div className={`p-3 rounded-2xl border ${isNight ? "bg-slate-900/80 border-slate-800" : "bg-white border-slate-200/80 shadow-2xs"} space-y-1.5`}>
        <div className="text-[10px] font-bold uppercase tracking-wider opacity-60">System Resources</div>
        <div className="flex justify-between text-xs">
          <span className="opacity-70 text-[11px]">System RAM</span>
          <span className="font-mono text-[11px] font-semibold">{brainStatus?.ram_usage || "Unavailable"}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="opacity-70 text-[11px]">GPU / VRAM</span>
          <span className="font-mono text-[11px] font-semibold">{brainStatus?.vram_usage || "Unavailable"}</span>
        </div>
      </div>

      {/* 5. Emotional Intelligence Card */}
      <div className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-2xl p-4 shadow-md space-y-2 relative overflow-hidden">
        <div className="flex justify-between items-center text-xs">
          <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">Detected Emotion</span>
          <span className="text-[9px] bg-white/20 px-2 py-0.5 rounded-full font-bold">
            {Math.round((emotion?.intensity || 0.3) * 100)}% Intensity
          </span>
        </div>
        
        <div className="text-base font-black capitalize flex items-center gap-1.5">
          <span>{emotion?.emotion === "celebrating" ? "🎉" : emotion?.emotion === "frustrated" ? "🔥" : emotion?.emotion === "sad" ? "💙" : emotion?.emotion === "curious" ? "✨" : "🌿"}</span>
          <span>{emotion?.emotion || "Neutral"}</span>
        </div>

        <div className="text-[10px] opacity-90">
          Cause: {emotion?.cause || "Casual conversation"}
        </div>

        {emotion?.needs && emotion.needs.length > 0 && (
          <div className="pt-1 flex flex-wrap gap-1">
            {emotion.needs.map((need, i) => (
              <span key={i} className="text-[9px] font-bold bg-white/20 text-white px-2 py-0.5 rounded-full">
                #{need}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 6. Social Energy Gauges */}
      <div className={`p-3.5 rounded-2xl border ${isNight ? "bg-slate-900/80 border-slate-800" : "bg-white border-slate-200/80 shadow-2xs"} space-y-2`}>
        <div className="text-[10px] font-bold uppercase tracking-wider opacity-60">Social Energy Posture</div>
        
        <div className="space-y-1">
          <div className="flex justify-between text-[9px] font-bold opacity-70">
            <span>❤️ WARMTH</span>
            <span>{Math.round((social?.warmth || 0.85) * 100)}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
            <div className="bg-rose-500 h-full rounded-full transition-all duration-500" style={{ width: `${(social?.warmth || 0.85) * 100}%` }}></div>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[9px] font-bold opacity-70">
            <span>⚡ CONVERSATION ENERGY</span>
            <span>{Math.round((social?.energy || 0.75) * 100)}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
            <div className="bg-amber-500 h-full rounded-full transition-all duration-500" style={{ width: `${(social?.energy || 0.75) * 100}%` }}></div>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[9px] font-bold opacity-70">
            <span>🎭 PLAYFULNESS</span>
            <span>{Math.round((social?.playfulness || 0.60) * 100)}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
            <div className="bg-cyan-500 h-full rounded-full transition-all duration-500" style={{ width: `${(social?.playfulness || 0.60) * 100}%` }}></div>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[9px] font-bold opacity-70">
            <span>🎯 SERIOUSNESS</span>
            <span>{Math.round((social?.seriousness || 0.45) * 100)}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
            <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${(social?.seriousness || 0.45) * 100}%` }}></div>
          </div>
        </div>
      </div>
    </aside>
  );
}
