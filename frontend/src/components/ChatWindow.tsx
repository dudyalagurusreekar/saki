import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import InputBox from "./InputBox";
import { streamChat } from "../lib/api";

export default function ChatWindow() {
  const [messages, setMessages] = useState<{role: string, content: string}[]>([
    { role: "assistant", content: "Hi there! I'm Saki. How can I help you today?" }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [uiMode, setUiMode] = useState<"saki" | "chatgpt">("saki");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, uiMode]);

  const sendMessage = async (text: string) => {
    const newMessages = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setIsTyping(true);

    let assistantText = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const lastMessage = newMessages[newMessages.length - 1]?.content || text;
      await streamChat(lastMessage, (chunk) => {
        setIsTyping(false);
        assistantText += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1].content = assistantText;
          return updated;
        });
      });
    } catch (error) {
      console.error("Error streaming chat:", error);
    } finally {
      setIsTyping(false);
    }
  };

  if (uiMode === "chatgpt") {
    return (
      <div className="flex h-screen bg-white">
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
              <MessageBubble key={i} role={m.role} text={m.content} uiMode="chatgpt" />
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
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
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
    <div className="flex flex-col h-screen w-full max-w-5xl mx-auto overflow-hidden relative">
      <button 
        onClick={() => setUiMode("chatgpt")}
        className="fixed top-4 right-4 z-50 px-4 py-2 bg-slate-800 text-white rounded-full text-sm font-bold shadow-lg hover:bg-slate-700 transition"
      >
        Switch to ChatGPT
      </button>

      {/* Realistic Sky Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none bg-gradient-to-b from-blue-300 to-blue-100">
        {/* Sun */}
        <div className="absolute top-[10%] left-[20%] w-32 h-32 bg-yellow-50 rounded-full blur-[4px] shadow-[0_0_100px_rgba(255,255,150,1)]"></div>
        
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

      {/* Premium Header */}
      <div className="flex-shrink-0 flex items-center justify-between p-4 md:px-8 mt-2 glass-panel mx-4 rounded-2xl z-10 shadow-[0_4px_15px_rgba(0,0,0,0.05)] mt-16 md:mt-2">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="h-12 w-12 rounded-full overflow-hidden border-2 border-[rgba(109,40,217,0.3)] shadow-[0_0_15px_rgba(109,40,217,0.2)] bg-white">
              <img src="/logo.png" alt="Saki" className="h-full w-full object-contain" />
            </div>
            <div className="absolute bottom-0 right-0 h-3 w-3 bg-green-400 rounded-full border-2 border-white status-indicator"></div>
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-600 to-violet-600 bg-clip-text text-transparent">
              Saki AI
            </h1>
            <p className="text-xs text-slate-600 font-medium">Online • Peaceful Sky</p>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 z-0 pb-32 scroll-smooth">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} text={m.content} uiMode="saki" />
        ))}
        {isTyping && (
          <div className="flex w-full mb-4 justify-start animate-slide-up">
            <div className="flex-shrink-0 mr-3">
              <div className="h-8 w-8 rounded-full overflow-hidden border border-[rgba(6,182,212,0.3)] bg-white">
                <img src="/logo.png" alt="Saki" className="h-full w-full object-contain opacity-90" />
              </div>
            </div>
            <div className="glass-panel text-slate-600 rounded-2xl rounded-bl-sm px-5 py-3.5 flex items-center gap-1 shadow-[0_4px_15px_rgba(0,0,0,0.05)]">
              <span className="animate-bounce inline-block w-1.5 h-1.5 bg-cyan-400 rounded-full"></span>
              <span className="animate-bounce inline-block w-1.5 h-1.5 bg-cyan-400 rounded-full" style={{ animationDelay: '0.2s' }}></span>
              <span className="animate-bounce inline-block w-1.5 h-1.5 bg-cyan-400 rounded-full" style={{ animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-blue-100 via-blue-100 to-transparent z-10">
        <InputBox onSend={sendMessage} uiMode="saki" />
      </div>
    </div>
  );
}
