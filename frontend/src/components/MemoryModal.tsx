import { useState } from "react";
import { SakiTheme } from "../lib/theme";

interface MemoryItem {
  id?: string;
  type?: string;
  content?: string;
  importance?: number;
  confidence?: number;
}

interface MemoryData {
  categorized?: {
    projects?: MemoryItem[];
    preferences?: MemoryItem[];
    decisions?: MemoryItem[];
    facts?: MemoryItem[];
    progress?: MemoryItem[];
  };
}

interface MemoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  memoryData: MemoryData | null;
  theme?: SakiTheme;
}

export default function MemoryModal({
  isOpen,
  onClose,
  memoryData,
  theme = "night_sky",
}: MemoryModalProps) {
  const isNight = theme === "night_sky";
  const [activeTab, setActiveTab] = useState<"projects" | "preferences" | "decisions" | "facts" | "progress">("projects");
  const [searchTerm, setSearchTerm] = useState("");

  if (!isOpen) return null;

  const categorized = memoryData?.categorized || {};

  const getItemsForTab = (): MemoryItem[] => {
    switch (activeTab) {
      case "projects": return categorized.projects || [];
      case "preferences": return categorized.preferences || [];
      case "decisions": return categorized.decisions || [];
      case "facts": return categorized.facts || [];
      case "progress": return categorized.progress || [];
      default: return [];
    }
  };

  const rawItems = getItemsForTab();
  const items = searchTerm.trim() 
    ? rawItems.filter((it) => (it.content || "").toLowerCase().includes(searchTerm.toLowerCase()))
    : rawItems;

  const tabs: Array<{ id: "projects" | "preferences" | "decisions" | "facts" | "progress"; label: string; icon: string }> = [
    { id: "projects", label: "Projects", icon: "📁" },
    { id: "preferences", label: "Preferences", icon: "⚙️" },
    { id: "decisions", label: "Decisions", icon: "💡" },
    { id: "facts", label: "Facts", icon: "📌" },
    { id: "progress", label: "Progress", icon: "📈" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fade-in select-none">
      <div 
        className={`w-full max-w-xl rounded-2xl p-5 shadow-2xl border hud-panel-glow flex flex-col max-h-[85vh] hud-corner-bracket transition-colors duration-300 ${
          isNight ? "text-slate-100" : "text-slate-900"
        }`}
        data-theme={theme}
      >
        {/* Header */}
        <div className={`flex items-center justify-between pb-3.5 border-b ${isNight ? "border-cyan-500/20" : "border-sky-200/80"}`}>
          <div className="flex items-center gap-2.5">
            <div className={`h-8 w-8 rounded-lg border flex items-center justify-center font-bold text-sm shadow-sm ${
              isNight ? "bg-cyan-950/80 border-cyan-500/40 text-cyan-300" : "bg-sky-100 border-sky-400 text-sky-700"
            }`}>
              🧠
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="hud-label font-bold text-[10px]">MEMORY // ARCHIVE</span>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#38bdf8]" />
              </div>
              <p className={`text-[10px] font-mono ${isNight ? "text-slate-400" : "text-slate-600"}`}>
                Durable Cross-Session Cognitive Store
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-1 rounded-lg font-mono transition text-xs ${
              isNight ? "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60" : "text-slate-500 hover:text-sky-900 hover:bg-slate-200/70"
            }`}
          >
            ✕
          </button>
        </div>

        {/* Search */}
        <div className="my-3">
          <input
            type="text"
            placeholder="Search memory records..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full py-1.5 px-3 rounded-lg text-xs border font-mono focus:outline-none transition ${
              isNight
                ? "bg-slate-900/80 border-cyan-500/25 text-white placeholder-slate-500 focus:border-cyan-400/60"
                : "bg-white/80 border-sky-300 text-slate-900 placeholder-slate-400 focus:border-sky-500"
            }`}
          />
        </div>

        {/* Tabs */}
        <div className={`flex gap-1.5 overflow-x-auto pb-2 border-b ${isNight ? "border-cyan-500/15" : "border-sky-200/60"}`}>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const count = (categorized[tab.id] || []).length;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-bold transition flex items-center gap-1.5 whitespace-nowrap ${
                  isActive
                    ? isNight
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-400 shadow-[0_0_10px_rgba(56,189,248,0.2)]"
                      : "bg-sky-500/20 text-sky-800 border border-sky-500 shadow-[0_0_10px_rgba(14,165,233,0.2)]"
                    : isNight
                    ? "bg-slate-900/50 text-slate-400 hover:text-slate-200 border border-transparent hover:border-slate-700"
                    : "bg-white/60 text-slate-600 hover:text-slate-900 border border-transparent hover:border-sky-300"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label} ({count})</span>
              </button>
            );
          })}
        </div>

        {/* Items List */}
        <div className="flex-1 overflow-y-auto py-3 space-y-2 pr-1">
          {items.length > 0 ? (
            items.map((it, idx) => (
              <div
                key={it.id || idx}
                className="p-3 rounded-xl hud-card border space-y-1.5"
              >
                <div className="flex justify-between items-start">
                  <span className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border ${
                    isNight
                      ? "bg-cyan-950/80 text-cyan-300 border-cyan-500/30"
                      : "bg-sky-100 text-sky-800 border-sky-300"
                  }`}>
                    {it.type || activeTab}
                  </span>
                  {it.importance !== undefined && (
                    <span className={`text-[9px] font-mono ${isNight ? "text-slate-400" : "text-slate-500"}`}>
                      IMP: {Math.round(it.importance * 100)}%
                    </span>
                  )}
                </div>
                <p className={`text-xs leading-relaxed font-mono ${isNight ? "text-slate-200" : "text-slate-800"}`}>
                  {it.content}
                </p>
              </div>
            ))
          ) : (
            <div className={`text-center py-8 italic text-xs font-mono ${isNight ? "text-slate-500" : "text-slate-400"}`}>
              No memory records found in this category.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
