import { useState, useEffect } from "react";
import { 
  GroupedConversations, 
  ConversationSummary, 
  searchConversations, 
  deleteConversation 
} from "../lib/api";
import { SakiTheme } from "../lib/theme";

interface SearchResultItem {
  id: string;
  title: string;
  updated_at?: number;
  snippet: string;
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: GroupedConversations | null;
  activeConversationId: string;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onOpenMemory: () => void;
  onOpenSettings: () => void;
  onOpenProjects: () => void;
  onToggleVoice?: () => void;
  isVoiceActive?: boolean;
  activeProject?: string;
  theme?: SakiTheme;
  activeView?: "chat" | "core";
  onSelectView?: (v: "chat" | "core") => void;
}

export default function Sidebar({
  isOpen,
  onClose,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onOpenMemory,
  onOpenSettings,
  onOpenProjects,
  onToggleVoice,
  isVoiceActive = false,
  activeProject,
  theme = "night_sky",
  activeView = "chat",
  onSelectView,
}: SidebarProps) {
  const isNight = theme === "night_sky";
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Debounced search
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (!trimmed) {
      const emptyTimer = setTimeout(() => {
        setSearchResults([]);
        setIsSearching(false);
      }, 0);
      return () => clearTimeout(emptyTimer);
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      const res = await searchConversations(trimmed);
      setSearchResults(res.results || []);
      setIsSearching(false);
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Delete this conversation record?")) {
      const ok = await deleteConversation(id);
      if (ok && id === activeConversationId) {
        onNewChat();
      }
    }
  };

  const renderConversationItem = (c: ConversationSummary) => {
    const isActive = c.id === activeConversationId;
    return (
      <div
        key={c.id}
        onClick={() => {
          onSelectConversation(c.id);
          if (typeof window !== "undefined" && window.innerWidth < 1024) onClose();
        }}
        className={`group relative flex items-center justify-between p-2 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 ${
          isActive
            ? isNight
              ? "bg-cyan-950/50 text-cyan-200 border border-cyan-500/40 shadow-[0_0_15px_rgba(56,189,248,0.15)]"
              : "bg-sky-100/90 text-sky-950 border border-sky-400/60 shadow-[0_0_12px_rgba(14,165,233,0.2)] font-bold"
            : isNight
            ? "text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent hover:border-slate-700/50"
            : "text-slate-700 hover:bg-white/80 hover:text-slate-900 border border-transparent hover:border-sky-200"
        }`}
      >
        {/* Active indicator bar */}
        {isActive && (
          <div className={`absolute left-0 inset-y-1.5 w-1 rounded-r ${isNight ? "bg-cyan-400 shadow-[0_0_8px_#38bdf8]" : "bg-sky-500 shadow-[0_0_8px_#0284c7]"}`} />
        )}

        <div className="flex items-center gap-2 truncate flex-1 min-w-0 pl-1">
          <span className={`text-[11px] ${isNight ? "text-cyan-400 opacity-70" : "text-sky-600 font-bold"}`}>◇</span>
          <span className="truncate">{c.title || "Conversation"}</span>
        </div>

        <button
          suppressHydrationWarning
          onClick={(e) => handleDelete(e, c.id)}
          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-500 p-1 rounded transition text-[11px] flex-shrink-0"
          title="Delete conversation"
        >
          ✕
        </button>
      </div>
    );
  };

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        suppressHydrationWarning
        className={`fixed lg:static inset-y-0 left-0 flex-shrink-0 flex flex-col h-full z-40 transition-all duration-300 ease-in-out border-r hud-panel select-none ${
          isNight ? "text-slate-200 border-cyan-500/15" : "text-slate-800 border-sky-300/40"
        } ${
          isOpen ? "translate-x-0" : "-translate-x-full lg:hidden"
        } ${isCollapsed ? "w-[72px]" : "w-[280px]"}`}
      >
        {/* Top Header: Sci-Fi Workstation Insignia */}
        <div className={`p-3.5 border-b flex items-center justify-between ${isNight ? "border-cyan-500/15" : "border-sky-200/60"}`}>
          {!isCollapsed ? (
            <div className="flex items-center gap-2.5 min-w-0">
              <div className={`relative h-8 w-8 rounded-lg overflow-hidden border flex-shrink-0 ${
                isNight ? "border-cyan-400/40 shadow-[0_0_12px_rgba(56,189,248,0.3)]" : "border-sky-400 shadow-sm"
              }`}>
                <img src="/saki.webp" alt="Saki Core" className="h-full w-full object-cover" />
                <div className={`absolute inset-0 pointer-events-none ${isNight ? "bg-cyan-500/10" : "bg-sky-500/5"}`} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="hud-label font-bold text-[10px]">SAKI // OS</span>
                  <span className={`inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 animate-pulse shadow-[0_0_6px_#38bdf8]" : "bg-sky-500 shadow-[0_0_6px_#0284c7]"}`} />
                </div>
                <div className={`text-[11px] font-extrabold tracking-wide truncate ${isNight ? "text-slate-100" : "text-slate-900"}`}>
                  WORKSTATION
                </div>
              </div>
            </div>
          ) : (
            <div className={`mx-auto h-8 w-8 rounded-lg overflow-hidden border ${isNight ? "border-cyan-400/40 shadow-[0_0_10px_rgba(56,189,248,0.3)]" : "border-sky-400"}`}>
              <img src="/saki.webp" alt="Saki" className="h-full w-full object-cover" />
            </div>
          )}

          <div className="flex items-center gap-1">
            {/* Desktop Collapse Toggle */}
            <button
              suppressHydrationWarning
              onClick={() => setIsCollapsed(!isCollapsed)}
              className={`hidden lg:flex p-1.5 rounded-lg transition text-xs ${
                isNight ? "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60" : "text-slate-500 hover:text-sky-800 hover:bg-white/70"
              }`}
              title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isCollapsed ? "»" : "«"}
            </button>

            {/* Mobile Close Button */}
            <button
              suppressHydrationWarning
              onClick={onClose}
              className={`lg:hidden p-1 rounded-md ${isNight ? "text-slate-400 hover:text-white" : "text-slate-600 hover:text-slate-900"}`}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Primary Action Button: New Chat */}
        <div className={`p-3 border-b ${isNight ? "border-cyan-500/10" : "border-sky-200/50"}`}>
          <button
            suppressHydrationWarning
            onClick={() => {
              onNewChat();
              if (typeof window !== "undefined" && window.innerWidth < 1024) onClose();
            }}
            className={`w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md transition flex items-center justify-center gap-2 transform active:scale-98 ${
              isCollapsed ? "px-0" : ""
            }`}
            title="New Conversation (Ctrl+K)"
          >
            <span className="text-base font-light leading-none">+</span>
            {!isCollapsed && (
              <>
                <span className="tracking-wide">New Session</span>
                <span className="text-[9px] font-mono opacity-80 bg-black/25 px-1.5 py-0.5 rounded border border-white/20 ml-auto">
                  ⌘K
                </span>
              </>
            )}
          </button>

          {/* Primary View Switcher Navigation */}
          {onSelectView && (
            <div className="grid grid-cols-2 gap-1 mt-2 pt-2 border-t border-cyan-500/10">
              <button
                type="button"
                onClick={() => {
                  onSelectView("chat");
                  if (typeof window !== "undefined" && window.innerWidth < 1024) onClose();
                }}
                className={`py-1.5 px-2 rounded-lg font-mono text-[11px] font-bold transition flex items-center justify-center gap-1.5 border ${
                  activeView === "chat"
                    ? isNight
                      ? "bg-cyan-950/70 text-cyan-300 border-cyan-500/40 shadow-[0_0_8px_rgba(56,189,248,0.2)]"
                      : "bg-sky-500 text-white border-sky-600 shadow-xs"
                    : isNight
                      ? "border-transparent text-slate-400 hover:text-white hover:bg-slate-800/60"
                      : "border-transparent text-slate-600 hover:text-slate-900 hover:bg-white/80"
                }`}
                title="Chat Workspace (ChatGPT Style)"
              >
                <span>💬</span>
                {!isCollapsed && <span>Chat</span>}
              </button>
              <button
                type="button"
                onClick={() => {
                  onSelectView("core");
                  if (typeof window !== "undefined" && window.innerWidth < 1024) onClose();
                }}
                className={`py-1.5 px-2 rounded-lg font-mono text-[11px] font-bold transition flex items-center justify-center gap-1.5 border ${
                  activeView === "core"
                    ? isNight
                      ? "bg-cyan-950/70 text-cyan-300 border-cyan-500/40 shadow-[0_0_8px_rgba(56,189,248,0.2)]"
                      : "bg-sky-500 text-white border-sky-600 shadow-xs"
                    : isNight
                      ? "border-transparent text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60"
                      : "border-transparent text-slate-600 hover:text-sky-800 hover:bg-white/80"
                }`}
                title="Dedicated Saki Core Interface (Pure Black)"
              >
                <span>⚛️</span>
                {!isCollapsed && <span>Core</span>}
              </button>
            </div>
          )}
        </div>

        {/* Search Filter (when expanded) */}
        {!isCollapsed && (
          <div className="px-3 pt-2.5 pb-1">
            <div className="relative">
              <input
                suppressHydrationWarning
                type="text"
                placeholder="Search telemetry & logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={`w-full py-1.5 pl-7 pr-7 rounded-lg text-xs border focus:outline-none transition font-mono ${
                  isNight
                    ? "bg-slate-900/80 border-cyan-500/20 text-white placeholder-slate-500 focus:border-cyan-400/60"
                    : "bg-white/80 border-sky-300 text-slate-900 placeholder-slate-400 focus:border-sky-500"
                }`}
              />
              <span className={`absolute left-2.5 top-2 text-[10px] ${isNight ? "text-cyan-400/60" : "text-sky-500"}`}>◇</span>
              {searchQuery && (
                <button 
                  suppressHydrationWarning
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-1.5 text-[10px] text-slate-400 hover:text-rose-500"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        )}

        {/* Conversation List / Search Results */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {!isCollapsed ? (
            searchQuery ? (
              <div className="space-y-1.5">
                <div className="hud-label px-1 flex justify-between">
                  <span>Search Results</span>
                  <span>{isSearching ? "..." : searchResults.length}</span>
                </div>
                {searchResults.length > 0 ? (
                  searchResults.map((r) => (
                    <div
                      key={r.id}
                      onClick={() => {
                        onSelectConversation(r.id);
                        setSearchQuery("");
                        if (typeof window !== "undefined" && window.innerWidth < 1024) onClose();
                      }}
                      className={`p-2 rounded-xl text-xs cursor-pointer border transition ${
                        isNight
                          ? "hover:bg-slate-800/80 border-transparent hover:border-cyan-500/30"
                          : "hover:bg-white/90 border-transparent hover:border-sky-300"
                      }`}
                    >
                      <div className={`font-semibold truncate ${isNight ? "text-cyan-200" : "text-sky-900"}`}>
                        {r.title}
                      </div>
                      <div className={`text-[10px] truncate mt-0.5 ${isNight ? "text-slate-400" : "text-slate-600"}`}>
                        {r.snippet}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-[11px] text-slate-400 text-center py-4 font-mono">
                    No records found
                  </div>
                )}
              </div>
            ) : conversations ? (
              <div className="space-y-3.5">
                {/* Today */}
                {conversations.today && conversations.today.length > 0 && (
                  <div className="space-y-1">
                    <div className="hud-label px-1">Today</div>
                    {conversations.today.map(renderConversationItem)}
                  </div>
                )}

                {/* Yesterday */}
                {conversations.yesterday && conversations.yesterday.length > 0 && (
                  <div className="space-y-1">
                    <div className="hud-label px-1">Yesterday</div>
                    {conversations.yesterday.map(renderConversationItem)}
                  </div>
                )}

                {/* Older */}
                {conversations.older && conversations.older.length > 0 && (
                  <div className="space-y-1">
                    <div className="hud-label px-1">Older Activity</div>
                    {conversations.older.map(renderConversationItem)}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-400 text-xs font-mono">
                Loading history...
              </div>
            )
          ) : (
            /* Collapsed Quick Actions */
            <div className="flex flex-col items-center gap-3">
              <button
                onClick={onOpenProjects}
                className={`p-2.5 rounded-xl transition ${isNight ? "hover:bg-slate-800/80 text-cyan-400" : "hover:bg-sky-100 text-sky-700"}`}
                title="Projects"
              >
                📁
              </button>
              <button
                onClick={onOpenMemory}
                className={`p-2.5 rounded-xl transition ${isNight ? "hover:bg-slate-800/80 text-purple-400" : "hover:bg-purple-100 text-purple-700"}`}
                title="Memory Vault"
              >
                🧠
              </button>
              <button
                onClick={onOpenSettings}
                className={`p-2.5 rounded-xl transition ${isNight ? "hover:bg-slate-800/80 text-slate-400 hover:text-white" : "hover:bg-slate-200 text-slate-600"}`}
                title="Settings"
              >
                ⚙️
              </button>
            </div>
          )}
        </div>

        {/* Footer Navigation & Capabilities Panel */}
        {!isCollapsed && (
          <div className={`p-3 border-t space-y-1 ${isNight ? "border-cyan-500/15 bg-slate-950/40" : "border-sky-200/60 bg-sky-50/60"}`}>
            {/* Active Project Indicator */}
            <button
              suppressHydrationWarning
              onClick={onOpenProjects}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                isNight ? "hover:bg-slate-800/60 text-slate-300 hover:text-white" : "hover:bg-white/80 text-slate-700 hover:text-slate-950"
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                <span className="text-cyan-500 text-xs">📁</span>
                <span className="truncate font-mono">{activeProject || "Default Workspace"}</span>
              </div>
              <span className={`text-[9px] font-mono border px-1 rounded ${isNight ? "text-cyan-400/70 border-cyan-500/30" : "text-sky-700 border-sky-300"}`}>
                PROJ
              </span>
            </button>

            {/* Memory Vault Trigger */}
            <button
              suppressHydrationWarning
              onClick={onOpenMemory}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                isNight ? "hover:bg-slate-800/60 text-slate-300 hover:text-white" : "hover:bg-white/80 text-slate-700 hover:text-slate-950"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-purple-500 text-xs">🧠</span>
                <span>Memory Vault</span>
              </div>
              <span className={`text-[9px] font-mono border px-1 rounded ${isNight ? "text-purple-400/70 border-purple-500/30" : "text-purple-700 border-purple-300"}`}>
                DURABLE
              </span>
            </button>

            {/* Voice Engine Toggle */}
            {onToggleVoice && (
              <button
                suppressHydrationWarning
                onClick={onToggleVoice}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  isVoiceActive
                    ? "bg-rose-950/50 text-rose-300 border border-rose-500/40"
                    : isNight
                    ? "hover:bg-slate-800/60 text-slate-300 hover:text-white"
                    : "hover:bg-white/80 text-slate-700 hover:text-slate-950"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs">{isVoiceActive ? "🎙️" : "🔈"}</span>
                  <span>Voice Engine</span>
                </div>
                <span className={`text-[9px] font-mono px-1 rounded ${
                  isVoiceActive ? "text-rose-400 font-bold animate-pulse" : "text-slate-400 border border-slate-400/40"
                }`}>
                  {isVoiceActive ? "LISTENING" : "STANDBY"}
                </span>
              </button>
            )}

            {/* Settings Trigger */}
            <button
              suppressHydrationWarning
              onClick={onOpenSettings}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                isNight ? "hover:bg-slate-800/60 text-slate-300 hover:text-white" : "hover:bg-white/80 text-slate-700 hover:text-slate-950"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-xs">⚙️</span>
                <span>System Config</span>
              </div>
              <span className={`text-[9px] font-mono ${isNight ? "text-slate-500" : "text-slate-500"}`}>v2.0</span>
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
