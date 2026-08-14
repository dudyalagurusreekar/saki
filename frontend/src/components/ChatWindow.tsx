import { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import InputBox from "./InputBox";
import { streamChat, getConfig, getMemory, ChatAttachment } from "../lib/api";

interface Message {
  role: string;
  content: string;
  attachments?: ChatAttachment[];
}

interface SystemConfig {
  privacy_mode: string;
  model_fast: string;
  model_emo: string;
  max_memory: number;
}

interface UserMemory {
  recent_mood: string;
  interests: string[];
  memories: unknown[];
  user_model?: {
    technical_depth: number;
    curiosity: number;
  };
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi there! I'm Saki. How can I help you today?" }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [uiMode, setUiMode] = useState<"saki" | "chatgpt">("saki");
  
  // Sidebar State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [userMemory, setUserMemory] = useState<UserMemory | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchMetadata = useCallback(async () => {
    try {
      const [configData, memoryData] = await Promise.all([
        getConfig().catch(() => null),
        getMemory().catch(() => null)
      ]);
      if (configData) setSystemConfig(configData);
      if (memoryData) setUserMemory(memoryData);
    } catch (err) {
      console.error("Failed to load metadata:", err);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      await fetchMetadata();
    };
    init();
  }, [fetchMetadata]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, uiMode, isSidebarOpen]);

  const sendMessage = async (text: string, attachments: ChatAttachment[]) => {
    const newMessages: Message[] = [...messages, { role: "user", content: text, attachments }];
    setMessages(newMessages);
    setIsTyping(true);

    let assistantText = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      await streamChat(text, attachments, (chunk) => {
        setIsTyping(false);
        assistantText += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1].content = assistantText;
          return updated;
        });
      });
      // After successfully getting a response, fetch metadata to sync memory/interests
      await fetchMetadata();
    } catch (error) {
      console.error("Error streaming chat:", error);
    } finally {
      setIsTyping(false);
    }
  };

  if (uiMode === "chatgpt") {
    return (
      <div className="flex h-screen bg-white font-sans text-gray-800">
        {/* Toggle Button */}
        <button 
          onClick={() => setUiMode("saki")}
          className="fixed top-4 right-4 z-50 px-4 py-2 bg-gray-100 text-gray-800 border border-gray-300 rounded-md text-sm font-medium shadow-sm hover:bg-gray-200 transition"
        >
          Switch to Sky Theme
        </button>

        {/* Sidebar (mock) */}
        <div className="hidden md:flex flex-col w-[260px] bg-[#202123] text-white">
          <div className="p-3">
            <button className="w-full flex items-center gap-3 border border-white/20 rounded-md py-3 px-3 text-sm hover:bg-white/5 transition">
              <span className="text-lg">+</span> New chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 text-sm text-gray-300">
            <div className="mb-4 text-xs font-semibold text-gray-500">Today</div>
            <div className="p-3 hover:bg-[#2A2B32] rounded-md cursor-pointer truncate">Peaceful Sky Theme</div>
          </div>
          <div className="p-4 border-t border-white/10 flex items-center gap-3">
            <div className="h-8 w-8 rounded-sm bg-purple-600 flex items-center justify-center font-bold text-sm">U</div>
            <span className="text-sm font-medium">User Account</span>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col h-full bg-white relative">
          <div className="flex-1 overflow-y-auto pb-32">
            {messages.map((m, i) => (
              <MessageBubble key={i} role={m.role} text={m.content} attachments={m.attachments} uiMode="chatgpt" />
            ))}
            {isTyping && (
              <div className="w-full py-6 px-4 md:px-0 bg-[#f7f7f8] border-y border-black/5">
                <div className="max-w-3xl mx-auto flex gap-4 md:gap-6 text-base">
                  <div className="flex-shrink-0">
                    <div className="h-[30px] w-[30px] rounded-sm bg-[#10a37f] p-0.5 overflow-hidden flex items-center justify-center">
                      <img src="/logo.png" alt="ChatGPT" className="h-full w-full object-contain bg-white rounded-sm" />
                    </div>
                  </div>
                  <div className="flex-1 flex items-center">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce mr-1"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce mr-1" style={{ animationDelay: "0.2s" }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce mr-3" style={{ animationDelay: "0.4s" }}></div>
                    <span className="text-xs text-gray-400 font-semibold animate-pulse">Saki is waking up / loading model...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-6">
            <InputBox onSend={sendMessage} uiMode="chatgpt" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden font-sans relative">
      
      {/* Realistic Sky Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none bg-gradient-to-b from-blue-300 to-blue-100">
        <div className="absolute top-[10%] left-[20%] w-32 h-32 bg-yellow-50 rounded-full blur-[4px] shadow-[0_0_100px_rgba(255,255,150,0.9)]"></div>
        
        {/* Clouds */}
        <div className="absolute top-[15%] w-[300px] h-[100px] bg-white rounded-full blur-[2px] opacity-90 animate-drift-slow flex items-center justify-center">
          <div className="absolute top-[-30px] left-[40px] w-[100px] h-[100px] bg-white rounded-full"></div>
          <div className="absolute top-[-50px] right-[60px] w-[120px] h-[120px] bg-white rounded-full"></div>
        </div>
        
        <div className="absolute top-[35%] w-[250px] h-[80px] bg-white rounded-full blur-[1px] opacity-80 animate-drift-medium" style={{ animationDelay: '-25s' }}>
          <div className="absolute top-[-20px] left-[30px] w-[80px] h-[80px] bg-white rounded-full"></div>
          <div className="absolute top-[-40px] right-[50px] w-[100px] h-[100px] bg-white rounded-full"></div>
        </div>
        
        <div className="absolute top-[5%] w-[400px] h-[120px] bg-white rounded-full blur-[3px] opacity-95 animate-drift-fast" style={{ animationDelay: '-10s' }}>
          <div className="absolute top-[-40px] left-[60px] w-[120px] h-[120px] bg-white rounded-full"></div>
          <div className="absolute top-[-60px] right-[80px] w-[150px] h-[150px] bg-white rounded-full"></div>
        </div>
      </div>

      {/* Floating Toggle Controls */}
      <div className="fixed top-4 right-4 z-40 flex items-center gap-3">
        <button 
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="px-4 py-2 bg-white/70 border border-slate-200/50 backdrop-blur-md text-slate-700 rounded-full text-sm font-bold shadow-md hover:bg-white transition flex items-center gap-1.5"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          {isSidebarOpen ? "Close Details" : "Show Details"}
        </button>

        <button 
          onClick={() => setUiMode("chatgpt")}
          className="px-4 py-2 bg-slate-800 text-white rounded-full text-sm font-bold shadow-md hover:bg-slate-700 transition"
        >
          Switch to ChatGPT
        </button>
      </div>

      {/* Collapsible Sidebar (Brain Panel) */}
      {isSidebarOpen && (
        <div className="w-[320px] flex-shrink-0 flex flex-col h-full sidebar-panel border-r border-slate-200/60 z-30 animate-slide-left p-6 overflow-y-auto">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-slate-200/60 pb-6 mb-6">
            <div className="h-10 w-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-black shadow-lg shadow-indigo-600/30">
              🧠
            </div>
            <div>
              <h2 className="font-extrabold text-slate-800 leading-tight">Brain Engine</h2>
              <p className="text-xs text-slate-500 font-semibold">Active Intelligence logs</p>
            </div>
          </div>

          {/* Config Settings Section */}
          <div className="space-y-4 mb-8">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider select-none">System Engine</h3>
            <div className="bg-white/80 border border-slate-100 rounded-2xl p-4 shadow-sm space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-500">Privacy Mode</span>
                <span className="font-extrabold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full uppercase tracking-wider text-[9px] border border-indigo-100">
                  {systemConfig?.privacy_mode || "MEDIUM"}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-500">Fast LLM Model</span>
                <span className="font-mono text-slate-600 text-[10px] bg-slate-100 px-2 py-0.5 rounded-md">
                  {systemConfig?.model_fast || "phi3"}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-500">Emo LLM Model</span>
                <span className="font-mono text-slate-600 text-[10px] bg-slate-100 px-2 py-0.5 rounded-md">
                  {systemConfig?.model_emo || "hermes2"}
                </span>
              </div>
            </div>
          </div>

          {/* User Memory & Traits Section */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider select-none">Durable Memories</h3>
            
            {/* Mood Card */}
            <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white rounded-2xl p-4 shadow-md space-y-2 relative overflow-hidden">
              <div className="absolute right-2 bottom-0 text-7xl opacity-10 select-none">👤</div>
              <div className="text-[10px] uppercase font-bold tracking-wider text-indigo-200">Current Mood Profile</div>
              <div className="text-xl font-black capitalize">{userMemory?.recent_mood || "Neutral"}</div>
              <div className="text-[10px] text-indigo-100 font-medium">Memory counts: {userMemory?.memories?.length || 0} facts</div>
            </div>

            {/* Interest Tags */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider select-none">Extracted Interests</span>
              <div className="flex flex-wrap gap-1.5">
                {userMemory?.interests && userMemory.interests.length > 0 ? (
                  userMemory.interests.map((interest: string, i: number) => (
                    <span key={i} className="text-[11px] font-semibold px-2.5 py-1 rounded-full memory-tag">
                      {interest}
                    </span>
                  ))
                ) : (
                  <span className="text-xs italic text-slate-400 py-1">No interests logged yet. Keep chatting!</span>
                )}
              </div>
            </div>

            {/* User Profile Model Indicators */}
            {userMemory?.user_model && (
              <div className="space-y-2 pt-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider select-none">Cognitive Metrics</span>
                <div className="bg-white/80 border border-slate-100 rounded-2xl p-4 shadow-sm space-y-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] font-bold text-slate-500">
                      <span>TECHNICAL DEPTH</span>
                      <span>{Math.round(userMemory.user_model.technical_depth * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: `${userMemory.user_model.technical_depth * 100}%` }}></div>
                    </div>
                  </div>
                  
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] font-bold text-slate-500">
                      <span>CURIOSITY INDEX</span>
                      <span>{Math.round(userMemory.user_model.curiosity * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-cyan-500 h-full rounded-full transition-all duration-500" style={{ width: `${userMemory.user_model.curiosity * 100}%` }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Chat Workspace */}
      <div className="flex-1 flex flex-col h-full bg-transparent overflow-hidden relative">
        
        {/* Premium Header */}
        <div className="flex-shrink-0 flex items-center justify-between p-4 md:px-8 mt-2 glass-panel mx-4 rounded-2xl z-10 shadow-[0_4px_15px_rgba(0,0,0,0.05)] mt-16 md:mt-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="h-12 w-12 rounded-full overflow-hidden border-2 border-[rgba(109,40,217,0.3)] shadow-[0_0_15px_rgba(109,40,217,0.2)] bg-white flex items-center justify-center">
                <img src="/logo.png" alt="Saki" className="h-full w-full object-contain" />
              </div>
              <div className="absolute bottom-0 right-0 h-3 w-3 bg-green-400 rounded-full border-2 border-white status-indicator"></div>
            </div>
            <div>
              <h1 className="text-xl font-extrabold bg-gradient-to-r from-cyan-600 to-indigo-600 bg-clip-text text-transparent">
                Saki AI
              </h1>
              <p className="text-xs text-slate-500 font-semibold">Online • Peaceful Sky</p>
            </div>
          </div>
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 z-0 pb-32 scroll-smooth">
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} text={m.content} attachments={m.attachments} uiMode="saki" />
          ))}
          {isTyping && (
            <div className="flex w-full mb-4 justify-start animate-slide-up">
              <div className="flex-shrink-0 mr-3">
                <div className="h-8 w-8 rounded-full overflow-hidden border border-[rgba(6,182,212,0.3)] bg-white flex items-center justify-center">
                  <img src="/logo.png" alt="Saki" className="h-full w-full object-contain opacity-90" />
                </div>
              </div>
              <div className="glass-panel text-slate-600 rounded-2xl rounded-bl-sm px-5 py-3.5 flex items-center gap-3 shadow-[0_4px_15px_rgba(0,0,0,0.05)]">
                <div className="flex gap-1">
                  <span className="animate-bounce inline-block w-1.5 h-1.5 bg-cyan-400 rounded-full"></span>
                  <span className="animate-bounce inline-block w-1.5 h-1.5 bg-cyan-400 rounded-full" style={{ animationDelay: '0.2s' }}></span>
                  <span className="animate-bounce inline-block w-1.5 h-1.5 bg-cyan-400 rounded-full" style={{ animationDelay: '0.4s' }}></span>
                </div>
                <span className="text-xs text-slate-500 font-semibold animate-pulse">Saki is waking up / loading model...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area Overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-blue-100/80 via-blue-100/50 to-transparent z-10 backdrop-blur-[2px]">
          <InputBox onSend={sendMessage} uiMode="saki" />
        </div>
      </div>
    </div>
  );
}
