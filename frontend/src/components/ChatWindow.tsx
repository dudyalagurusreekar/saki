import { useState, useRef, useEffect, useCallback } from "react";
import SkyBackground from "./SkyBackground";
import TopBar from "./TopBar";
import Sidebar from "./Sidebar";
import BrainPanel from "./BrainPanel";
import MessageBubble from "./MessageBubble";
import InputBox from "./InputBox";
import MemoryModal from "./MemoryModal";
import SettingsModal from "./SettingsModal";
import { 
  streamChat, 
  getHealth, 
  getBrainStatus, 
  getMemory, 
  getSettings, 
  saveSettings, 
  getConversations, 
  getConversation, 
  createConversation,
  ChatAttachment,
  GroupedConversations,
  BrainStatusData,
  AppSettings
} from "../lib/api";

interface Message {
  role: string;
  content: string;
  attachments?: ChatAttachment[];
}

interface MemoryDataStructure {
  name?: string | null;
  interests?: string[];
  recent_mood?: string;
  categorized?: {
    projects?: Array<{ id?: string; content?: string; type?: string; importance?: number }>;
    preferences?: Array<{ id?: string; content?: string; type?: string; importance?: number }>;
    decisions?: Array<{ id?: string; content?: string; type?: string; importance?: number }>;
    facts?: Array<{ id?: string; content?: string; type?: string; importance?: number }>;
    progress?: Array<{ id?: string; content?: string; type?: string; importance?: number }>;
  };
  awareness?: {
    current_activity?: string;
    current_project?: string;
    conversation_mode?: string;
    emotional_state?: {
      emotion: string;
      intensity: number;
      confidence: number;
      cause: string;
      needs: string[];
    };
    social_energy?: {
      energy: number;
      warmth: number;
      playfulness: number;
      seriousness: number;
    };
  };
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hey! Good to see you. What are we building or exploring today? 🌸" }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  
  // Layout toggles - consistent SSR default to prevent hydration mismatch
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isBrainOpen, setIsBrainOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Responsive sidebar check deferred to post-mount event loop
  useEffect(() => {
    const handleResize = () => {
      if (typeof window !== "undefined" && window.innerWidth < 1024) {
        setIsSidebarOpen(false);
      }
    };
    const timer = setTimeout(handleResize, 0);
    window.addEventListener("resize", handleResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // System & Telemetry Data
  const [healthStatus, setHealthStatus] = useState<"Online" | "Degraded" | "Offline">("Online");
  const [brainStatus, setBrainStatus] = useState<BrainStatusData | null>(null);
  const [userMemory, setUserMemory] = useState<MemoryDataStructure | null>(null);
  const [conversations, setConversations] = useState<GroupedConversations | null>(null);
  const [activeConvId, setActiveConvId] = useState<string>("default-session");

  // Settings & Theme
  const [appSettings, setAppSettings] = useState<AppSettings>({
    theme: "clear_sky",
    reduced_animation: false,
    personality_warmth: 0.85,
    personality_playfulness: 0.60,
    personality_verbosity: 0.60,
    privacy_mode: "local_only",
    auto_keep_alive: "5m"
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Synchronize telemetry and system status
  const refreshSystemData = useCallback(async () => {
    try {
      const [health, brain, mem, convs, settings] = await Promise.all([
        getHealth().catch(() => null),
        getBrainStatus().catch(() => null),
        getMemory().catch(() => null),
        getConversations().catch(() => null),
        getSettings().catch(() => null)
      ]);

      if (health) setHealthStatus(health.status);
      if (brain) setBrainStatus(brain);
      if (mem) setUserMemory(mem);
      if (convs) {
        setConversations(convs);
        if (!activeConvId || activeConvId === "default-session") {
          setActiveConvId(convs.active_id || "default-session");
        }
      }
      if (settings) setAppSettings((prev) => ({ ...prev, ...settings }));
    } catch (err) {
      console.error("Error refreshing telemetry:", err);
    }
  }, [activeConvId]);

  // Initial load and periodic health ping (every 10s)
  useEffect(() => {
    let isMounted = true;
    const loadInitial = async () => {
      if (isMounted) {
        await refreshSystemData();
      }
    };
    loadInitial();

    const interval = setInterval(async () => {
      const health = await getHealth();
      if (health && isMounted) setHealthStatus(health.status);
    }, 10000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [refreshSystemData]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, isSidebarOpen, isBrainOpen]);

  // Stop generation handler
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
  };

  // Switch Conversation
  const handleSelectConversation = async (id: string) => {
    handleStop();
    setActiveConvId(id);
    const detail = await getConversation(id);
    if (detail && detail.messages && detail.messages.length > 0) {
      setMessages(detail.messages);
    } else {
      setMessages([
        { role: "assistant", content: "Hey! Good to see you. What are we building or exploring today? 🌸" }
      ]);
    }
  };

  // New Chat
  const handleNewChat = async () => {
    handleStop();
    const newConv = await createConversation();
    if (newConv) {
      setActiveConvId(newConv.id);
      setMessages(newConv.messages || [
        { role: "assistant", content: "Hey! Good to see you. What are we building or exploring today? 🌸" }
      ]);
      const convs = await getConversations();
      if (convs) setConversations(convs);
    }
  };

  // Send Message
  const sendMessage = async (text: string, attachments: ChatAttachment[]) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const newMessages: Message[] = [...messages, { role: "user", content: text, attachments }];
    setMessages(newMessages);
    setIsTyping(true);

    let assistantText = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      await streamChat(
        text, 
        attachments, 
        (chunk) => {
          setIsTyping(false);
          assistantText += chunk;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1].content = assistantText;
            return updated;
          });
        },
        controller.signal,
        activeConvId
      );
      await refreshSystemData();
    } catch (error) {
      console.error("Error streaming message:", error);
    } finally {
      setIsTyping(false);
      abortControllerRef.current = null;
    }
  };

  // Retry last assistant message
  const handleRetry = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      sendMessage(lastUserMsg.content, lastUserMsg.attachments || []);
    }
  };

  // Update Settings
  const handleUpdateSettings = async (newSettings: Partial<AppSettings>) => {
    setAppSettings((prev) => ({ ...prev, ...newSettings }));
    await saveSettings(newSettings);
  };

  const isNight = appSettings.theme === "night_sky";

  return (
    <div className={`flex h-screen w-screen overflow-hidden font-sans relative ${isNight ? "dark text-slate-100" : "text-slate-800"}`} suppressHydrationWarning>
      
      {/* Dynamic Animated Sky Background */}
      <SkyBackground 
        theme={appSettings.theme} 
        reducedMotion={appSettings.reduced_animation} 
      />

      {/* Main 3-Region Layout */}
      <div className="flex h-full w-full overflow-hidden">
        
        {/* Left Sidebar */}
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          conversations={conversations}
          activeConversationId={activeConvId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
          onOpenMemory={() => setIsMemoryOpen(true)}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenProjects={() => setIsMemoryOpen(true)}
          theme={appSettings.theme}
        />

        {/* Central Chat Workspace */}
        <div className="flex-1 flex flex-col h-full overflow-hidden relative">
          
          {/* Top Bar */}
          <TopBar
            theme={appSettings.theme}
            onToggleTheme={() => handleUpdateSettings({ theme: isNight ? "clear_sky" : "night_sky" })}
            isSidebarOpen={isSidebarOpen}
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            isBrainOpen={isBrainOpen}
            onToggleBrain={() => setIsBrainOpen(!isBrainOpen)}
            healthStatus={healthStatus}
            mode={brainStatus?.mode || userMemory?.awareness?.conversation_mode || "casual"}
            activeProject={userMemory?.awareness?.current_project}
          />

          {/* Conversation Stream */}
          <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-4 z-0 pb-36 scroll-smooth">
            <div className="max-w-3xl w-full mx-auto space-y-3">
              {messages.map((m, i) => (
                <MessageBubble 
                  key={i} 
                  role={m.role} 
                  text={m.content} 
                  attachments={m.attachments} 
                  theme={appSettings.theme}
                  onRetry={i === messages.length - 1 && m.role === "assistant" ? handleRetry : undefined}
                />
              ))}
              
              {/* Typing indicator with Saki avatar */}
              {isTyping && (
                <div className="flex w-full mb-3 justify-start animate-slide-up">
                  <div className="flex-shrink-0 mr-2.5 mt-0.5">
                    <div className="h-8 w-8 rounded-full overflow-hidden border-2 border-indigo-400/50 bg-white flex items-center justify-center shadow-xs">
                      <img src="/saki.webp" alt="Saki" className="h-full w-full object-cover scale-105 opacity-90" />
                    </div>
                  </div>
                  <div className={`px-4 py-2.5 rounded-2xl rounded-bl-xs flex items-center gap-2.5 shadow-xs border backdrop-blur-md ${
                    isNight 
                      ? "bg-[#1c2541]/90 border-slate-700/80 text-slate-200" 
                      : "bg-white/90 border-slate-200/80 text-slate-600"
                  }`}>
                    <div className="flex gap-1">
                      <span className="animate-bounce inline-block w-1.5 h-1.5 bg-indigo-500 rounded-full"></span>
                      <span className="animate-bounce inline-block w-1.5 h-1.5 bg-indigo-500 rounded-full" style={{ animationDelay: '0.2s' }}></span>
                      <span className="animate-bounce inline-block w-1.5 h-1.5 bg-indigo-500 rounded-full" style={{ animationDelay: '0.4s' }}></span>
                    </div>
                    <span className="text-xs font-medium animate-pulse">Saki is thinking...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </main>

          {/* Bottom Floating Composer */}
          <footer className={`absolute bottom-0 left-0 right-0 p-4 z-10 backdrop-blur-xs ${
            isNight 
              ? "bg-gradient-to-t from-[#0b132b]/95 via-[#0b132b]/70 to-transparent" 
              : "bg-gradient-to-t from-[#bae6fd]/95 via-[#bae6fd]/70 to-transparent"
          }`}>
            <div className="max-w-3xl w-full mx-auto">
              <InputBox 
                onSend={sendMessage} 
                onStop={handleStop} 
                isGenerating={isTyping} 
                theme={appSettings.theme}
              />
            </div>
          </footer>
        </div>

        {/* Right Saki Brain Telemetry Panel */}
        <BrainPanel
          isOpen={isBrainOpen}
          onClose={() => setIsBrainOpen(false)}
          brainStatus={brainStatus}
          theme={appSettings.theme}
        />
      </div>

      {/* Modals */}
      <MemoryModal
        isOpen={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
        memoryData={userMemory}
        theme={appSettings.theme}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={appSettings}
        onUpdateSettings={handleUpdateSettings}
      />
    </div>
  );
}
