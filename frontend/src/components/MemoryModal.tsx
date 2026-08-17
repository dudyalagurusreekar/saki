import { useState } from "react";

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
  theme?: "clear_sky" | "night_sky";
}

export default function MemoryModal({
  isOpen,
  onClose,
  memoryData,
  theme = "clear_sky"
}: MemoryModalProps) {
  const [activeTab, setActiveTab] = useState<"projects" | "preferences" | "decisions" | "facts" | "progress">("projects");
  const [searchTerm, setSearchTerm] = useState("");

  if (!isOpen) return null;

  const isNight = theme === "night_sky";
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-fade-in">
      <div 
        className={`w-full max-w-xl rounded-3xl p-6 shadow-2xl border flex flex-col max-h-[85vh] ${
          isNight 
            ? "bg-[#111827] border-slate-700 text-slate-100" 
            : "bg-white border-slate-200 text-slate-800"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
              🧠
            </div>
            <div>
              <h2 className="text-base font-extrabold">Durable Memory Explorer</h2>
              <p className="text-xs opacity-60">Saki&apos;s long-term memory across projects &amp; preferences</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Search */}
        <div className="my-3">
          <input
            type="text"
            placeholder="Filter memories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={`w-full py-2 px-3.5 rounded-xl text-xs border focus:outline-none transition ${
              isNight 
                ? "bg-slate-800/80 border-slate-700 text-white placeholder-slate-500 focus:border-indigo-500" 
                : "bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:border-indigo-500"
            }`}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-1.5 overflow-x-auto pb-2 text-xs font-bold">
          <button
            onClick={() => setActiveTab("projects")}
            className={`px-3 py-1.5 rounded-xl transition ${
              activeTab === "projects" 
                ? "bg-indigo-600 text-white shadow-xs" 
                : isNight ? "bg-slate-800 text-slate-300 hover:bg-slate-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Projects ({categorized.projects?.length || 0})
          </button>

          <button
            onClick={() => setActiveTab("preferences")}
            className={`px-3 py-1.5 rounded-xl transition ${
              activeTab === "preferences" 
                ? "bg-indigo-600 text-white shadow-xs" 
                : isNight ? "bg-slate-800 text-slate-300 hover:bg-slate-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Preferences ({categorized.preferences?.length || 0})
          </button>

          <button
            onClick={() => setActiveTab("decisions")}
            className={`px-3 py-1.5 rounded-xl transition ${
              activeTab === "decisions" 
                ? "bg-indigo-600 text-white shadow-xs" 
                : isNight ? "bg-slate-800 text-slate-300 hover:bg-slate-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Decisions ({categorized.decisions?.length || 0})
          </button>

          <button
            onClick={() => setActiveTab("facts")}
            className={`px-3 py-1.5 rounded-xl transition ${
              activeTab === "facts" 
                ? "bg-indigo-600 text-white shadow-xs" 
                : isNight ? "bg-slate-800 text-slate-300 hover:bg-slate-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Facts ({categorized.facts?.length || 0})
          </button>
        </div>

        {/* Items List */}
        <div className="flex-1 overflow-y-auto space-y-2 py-2 pr-1">
          {items && items.length > 0 ? (
            items.map((m, i: number) => (
              <div 
                key={i} 
                className={`p-3 rounded-2xl border text-xs leading-relaxed ${
                  isNight 
                    ? "bg-slate-800/70 border-slate-700/80 text-slate-200" 
                    : "bg-slate-50 border-slate-200/80 text-slate-700"
                }`}
              >
                <div className="flex justify-between items-center mb-1 text-[10px] font-bold opacity-60">
                  <span className="uppercase">{m.type || activeTab}</span>
                  <span>Importance: {m.importance || 8}/10</span>
                </div>
                <div className="font-medium">{m.content}</div>
              </div>
            ))
          ) : (
            <div className="text-center py-10 opacity-50 text-xs italic">
              {searchTerm ? "No matching records found." : "No records in this category yet."}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-xs font-bold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
