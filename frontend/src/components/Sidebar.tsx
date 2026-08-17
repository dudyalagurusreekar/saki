import { useState, useEffect } from "react";
import { 
  GroupedConversations, 
  ConversationSummary, 
  searchConversations,
  deleteConversation 
} from "../lib/api";

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
  theme?: "clear_sky" | "night_sky";
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
  theme = "clear_sky"
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const isNight = theme === "night_sky";

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
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Delete this conversation?")) {
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
          if (typeof window !== "undefined" && window.innerWidth < 768) onClose();
        }}
        className={`group flex items-center justify-between p-2 rounded-xl text-xs font-semibold cursor-pointer transition ${
          isActive
            ? isNight
              ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40"
              : "bg-indigo-50 text-indigo-700 border border-indigo-200"
            : isNight
              ? "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        }`}
      >
        <div className="flex items-center gap-2 truncate flex-1 mr-1">
          <span className="opacity-60 text-[11px]">💬</span>
          <span className="truncate">{c.title || "Conversation"}</span>
        </div>

        <button
          suppressHydrationWarning
          onClick={(e) => handleDelete(e, c.id)}
          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 p-1 rounded transition text-[10px]"
          title="Delete chat"
        >
          🗑️
        </button>
      </div>
    );
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/30 backdrop-blur-xs z-30 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        suppressHydrationWarning
        className={`fixed md:static inset-y-0 left-0 w-[270px] flex-shrink-0 flex flex-col h-full z-40 transition-transform duration-300 ease-in-out border-r ${
          isOpen ? "translate-x-0" : "-translate-x-full md:hidden"
        } ${
          isNight 
            ? "bg-[#111827]/90 border-slate-800 text-slate-200 backdrop-blur-xl" 
            : "bg-white/85 border-slate-200/80 text-slate-800 backdrop-blur-xl shadow-lg md:shadow-none"
        }`}
      >
        {/* Sidebar Header & New Chat */}
        <div className="p-3.5 border-b border-slate-200/60 dark:border-slate-800/80 flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full overflow-hidden border border-indigo-400/40">
                <img src="/saki.webp" alt="Saki" className="h-full w-full object-cover" />
              </div>
              <span className="font-extrabold text-xs tracking-wider uppercase opacity-70">Saki Navigation</span>
            </div>

            <button
              suppressHydrationWarning
              onClick={onClose}
              className="md:hidden text-slate-400 hover:text-slate-700 p-1 rounded-md"
            >
              ✕
            </button>
          </div>

          <button
            suppressHydrationWarning
            onClick={() => {
              onNewChat();
              if (typeof window !== "undefined" && window.innerWidth < 768) onClose();
            }}
            className="w-full py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold text-xs shadow-md transition flex items-center justify-center gap-2 transform active:scale-98"
          >
            <span className="text-base font-light leading-none">+</span>
            <span>New Chat</span>
          </button>

          {/* Search Box */}
          <div className="relative">
            <input
              suppressHydrationWarning
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`w-full py-1.5 pl-7 pr-3 rounded-lg text-xs border focus:outline-none transition ${
                isNight 
                  ? "bg-slate-800/80 border-slate-700 text-white placeholder-slate-500 focus:border-indigo-500" 
                  : "bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:border-indigo-500"
              }`}
            />
            <span className="absolute left-2.5 top-2 text-[10px] opacity-40">🔍</span>
            {searchQuery && (
              <button 
                suppressHydrationWarning
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1.5 text-[10px] text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Conversation List / Search Results */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {searchQuery ? (
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">
                {isSearching ? "Searching..." : `Results (${searchResults.length})`}
              </div>
              {searchResults.length > 0 ? (
                searchResults.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => {
                      onSelectConversation(r.id);
                      setSearchQuery("");
                      if (typeof window !== "undefined" && window.innerWidth < 768) onClose();
                    }}
                    className={`p-2 rounded-xl text-xs cursor-pointer border transition ${
                      isNight ? "bg-slate-800/70 border-slate-700 text-slate-200" : "bg-slate-50 border-slate-200 text-slate-800"
                    }`}
                  >
                    <div className="font-bold truncate">{r.title}</div>
                    <div className="text-[10px] opacity-60 truncate mt-0.5">{r.snippet}</div>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-400 italic text-center py-4">No matching chats found.</div>
              )}
            </div>
          ) : (
            <>
              {/* Today */}
              {conversations?.today && conversations.today.length > 0 && (
                <div className="space-y-1">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">Today</div>
                  {conversations.today.map(renderConversationItem)}
                </div>
              )}

              {/* Yesterday */}
              {conversations?.yesterday && conversations.yesterday.length > 0 && (
                <div className="space-y-1 pt-1">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">Yesterday</div>
                  {conversations.yesterday.map(renderConversationItem)}
                </div>
              )}

              {/* Older */}
              {conversations?.older && conversations.older.length > 0 && (
                <div className="space-y-1 pt-1">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">Previous 7 Days</div>
                  {conversations.older.map(renderConversationItem)}
                </div>
              )}

              {!conversations?.today?.length && !conversations?.yesterday?.length && !conversations?.older?.length && (
                <div className="text-xs text-slate-400 text-center py-6 italic">No chats yet. Start chatting!</div>
              )}
            </>
          )}
        </div>

        {/* Footer Navigation Links */}
        <div className="p-3 border-t border-slate-200/60 dark:border-slate-800/80 space-y-1">
          <button
            suppressHydrationWarning
            onClick={onOpenProjects}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition ${
              isNight ? "text-slate-300 hover:bg-slate-800" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            <span>📁</span>
            <span>Projects &amp; Goals</span>
          </button>

          <button
            suppressHydrationWarning
            onClick={onOpenMemory}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition ${
              isNight ? "text-slate-300 hover:bg-slate-800" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            <span>🧠</span>
            <span>Durable Memory</span>
          </button>

          <button
            suppressHydrationWarning
            onClick={onOpenSettings}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition ${
              isNight ? "text-slate-300 hover:bg-slate-800" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            <span>⚙️</span>
            <span>Settings</span>
          </button>
        </div>
      </aside>
    </>
  );
}
