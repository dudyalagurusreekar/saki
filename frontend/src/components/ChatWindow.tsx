"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import SakiCorePage from "./SakiCorePage";
import TopBar from "./TopBar";
import Sidebar from "./Sidebar";
import BrainPanel from "./BrainPanel";
import MessageBubble from "./MessageBubble";
import InputBox from "./InputBox";
import MemoryModal from "./MemoryModal";
import SettingsModal from "./SettingsModal";
import SkyBackground from "./SkyBackground";
import { SakiVoicePlayer } from "./core/engine/SakiVoicePlayer";
import { 
  streamChat, 
  executeVoiceTurn,
  fetchSpeechAudio,
  interruptVoice,
  getHealth, 
  getBrainStatus, 
  getMemory, 
  getSettings, 
  saveSettings, 
  getConversations, 
  getConversation, 
  createConversation,
  subscribeToStateStream,
  ChatAttachment,
  GroupedConversations,
  BrainStatusData,
  AppSettings,
  SakiState,
  SakiEvent,
  VoiceTurnResponse
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

interface PipelineDiagnostics {
  stage: string;
  sttMs?: number;
  llmMs?: number;
  ttsMs?: number;
  totalMs?: number;
  model?: string;
  mode?: string;
  task?: string;
}

export default function ChatWindow({ initialView = "chat" }: { initialView?: "chat" | "core" }) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Saki Core online. Neural matrix initialized. Ready for operations and dialogue. 🌸" }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [sakiState, setSakiState] = useState<SakiState>("IDLE");
  const [sakiActivity, setSakiActivity] = useState<string>("");
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>("en");
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [lastTranscript, setLastTranscript] = useState<string>("");
  const [lastResponse, setLastResponse] = useState<string>("");
  const [diagnostics, setDiagnostics] = useState<PipelineDiagnostics | null>(null);
  
  // Primary Experience View: "chat" (practical workspace) vs "core" (dedicated black-screen visual presence)
  const [activeView, setActiveView] = useState<"chat" | "core">(initialView);
  
  // Layout toggles
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isBrainOpen, setIsBrainOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Responsive sidebar check
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

  // Wire SakiVoicePlayer state transitions to Saki State Engine
  useEffect(() => {
    SakiVoicePlayer.getInstance().setOnStateChange((state, activity) => {
      setSakiState(state);
      if (activity !== undefined) {
        setSakiActivity(activity);
      }
    });
    return () => {
      SakiVoicePlayer.getInstance().setOnStateChange(null);
    };
  }, []);

  // System & Telemetry Data
  const [healthStatus, setHealthStatus] = useState<"Online" | "Degraded" | "Offline">("Online");
  const [brainStatus, setBrainStatus] = useState<BrainStatusData | null>(null);
  const [userMemory, setUserMemory] = useState<MemoryDataStructure | null>(null);
  const [conversations, setConversations] = useState<GroupedConversations>({ today: [], yesterday: [], last_7_days: [], older: [] });
  const [activeConvId, setActiveConvId] = useState<string>("default-session");
  const [appSettings, setAppSettings] = useState<AppSettings>({
    theme: "night_sky",
    core_quality: "auto",
    core_opacity: 0.85,
    reduced_animation: false,
    audio_sensitivity: 1.0,
    voice_speed: 1.0,
    system_volume: 1.0,
    stt_model: "whisper-tiny",
    tts_voice: "af_heart"
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isNight = appSettings.theme === "night_sky";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Load telemetry & conversations
  const refreshSystemData = useCallback(async () => {
    try {
      const [h, b, m, s, c] = await Promise.all([
        getHealth(),
        getBrainStatus(),
        getMemory(),
        getSettings(),
        getConversations()
      ]);
      if (h?.status) setHealthStatus(h.status);
      if (b) setBrainStatus(b);
      if (m) setUserMemory(m as MemoryDataStructure);
      if (s) setAppSettings((prev) => ({ ...prev, ...s }));
      if (c) setConversations(c);
      if (c?.active_id) {
        setActiveConvId(c.active_id);
      }
    } catch (e) {
      console.warn("Telemetry fetch error:", e);
    }
  }, []);

  useEffect(() => {
    const initialTimer = setTimeout(refreshSystemData, 0);
    const interval = setInterval(refreshSystemData, 10000);
    return () => {
      clearTimeout(initialTimer);
      clearInterval(interval);
    };
  }, [refreshSystemData]);

  // SSE State Subscription
  useEffect(() => {
    const unsubscribe = subscribeToStateStream((event: SakiEvent) => {
      if (event.state) {
        setSakiState(event.state);
      }
      if (event.activity) {
        setSakiActivity(event.activity);
      }
      if (event.detected_language) {
        setDetectedLanguage(event.detected_language);
      }
    });
    return () => {
      unsubscribe();
    };
  }, []);

  const handleNewChat = useCallback(async () => {
    try {
      const res = await createConversation();
      if (res) {
        setActiveConvId(res.id);
        setMessages([{ role: "assistant", content: "New Saki workspace session initialized. 🌸" }]);
        setDiagnostics(null);
        refreshSystemData();
      }
    } catch (err) {
      console.error("Failed to start new session", err);
    }
  }, [refreshSystemData]);

  const handleSelectConversation = useCallback(async (id: string) => {
    try {
      const detail = await getConversation(id);
      if (detail) {
        setActiveConvId(detail.id);
        setMessages(
          detail.messages.length > 0 
            ? detail.messages 
            : [{ role: "assistant", content: `Session ${detail.title} restored. Ready.` }]
        );
      }
    } catch (err) {
      console.error("Failed to fetch conversation details", err);
    }
  }, []);

  const handleUpdateSettings = async (newSet: Partial<AppSettings>) => {
    setAppSettings((prev) => {
      const merged = { ...prev, ...newSet };
      saveSettings(merged).catch((e) => console.error("Save settings error:", e));
      return merged;
    });
  };

  const handleToggleVoice = () => {
    setIsVoiceActive((prev) => !prev);
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // Instant voice barge-in / audio halt (< 10ms)
    SakiVoicePlayer.getInstance().stopPlayback(true);
    interruptVoice(activeConvId).catch(() => {});
    setIsTyping(false);
    setSakiState("IDLE");
    setSakiActivity("Operation halted by user.");
  };

  // Unified voice turn handler (Faster-Whisper STT -> Saki Brain -> Kokoro TTS -> Web Audio Playback)
  const sendVoiceTurn = useCallback(async (audioBlob: Blob, audioBase64: string) => {
    if (!audioBase64) return;

    console.log(`[VAD Diagnostics] sendVoiceTurn called: audioBlobSize=${audioBlob?.size || 0} bytes, base64Length=${audioBase64.length}`);

    setIsTyping(true);
    setSakiState("THINKING");
    setSakiActivity("Transcribing speech and reasoning through neural matrix...");

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const turnRes: VoiceTurnResponse | null = await executeVoiceTurn(
        audioBase64,
        activeConvId,
        appSettings.tts_voice || "af_heart",
        appSettings.voice_speed || 1.0,
        controller.signal
      );

      if (turnRes && turnRes.success) {
        const transcript = turnRes.transcript?.trim();
        const responseText = turnRes.response_text?.trim();

        if (responseText) {
          setLastResponse(responseText);
        }

        if (transcript) {
          setLastTranscript(transcript);
          setMessages((prev) => [
            ...prev,
            { role: "user", content: transcript },
            { role: "assistant", content: responseText || "Voice turn processed." }
          ]);
        } else if (responseText) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: responseText }
          ]);
        }

        if (turnRes.selected_model) {
          const langDisplay = turnRes.output_language && turnRes.detected_language !== turnRes.output_language
            ? `${turnRes.detected_language.toUpperCase()} → ${turnRes.output_language.toUpperCase()}`
            : (turnRes.detected_language || "en").toUpperCase();

          setDiagnostics({
            stage: "COMPLETE",
            sttMs: turnRes.latencies?.stt_latency_ms,
            llmMs: turnRes.latencies?.llm_latency_ms,
            ttsMs: turnRes.latencies?.tts_latency_ms,
            totalMs: turnRes.latencies?.total_latency_ms,
            model: turnRes.selected_model,
            task: turnRes.task_type,
            mode: langDisplay
          });
        }

        if (turnRes.detected_language) {
          setDetectedLanguage(turnRes.detected_language);
        }

        // Play Kokoro / Indic TTS speech audio in browser
        if (turnRes.audio_base64) {
          setSakiState("SPEAKING");
          setSakiActivity(`Saki speaking (${turnRes.voice_used || "af_heart"})...`);
          
          await SakiVoicePlayer.getInstance().playSpeech(
            turnRes.audio_base64,
            () => {
              setSakiState("IDLE");
              setSakiActivity("Voice turn complete. Ready.");
            },
            (err) => {
              console.warn("Audio playback error:", err);
              setSakiState("IDLE");
              setSakiActivity("Voice turn complete.");
            }
          );
        } else {
          setSakiState("IDLE");
          setSakiActivity("Voice turn complete.");
        }

        refreshSystemData();
      } else {
        const errDetail = turnRes?.error || "No speech detected in audio stream.";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `🎙️ ${errDetail} Please speak clearly into your microphone.` }
        ]);
        setSakiState("IDLE");
        setSakiActivity("Ready.");
      }
    } catch (err: unknown) {
      if ((err as Error)?.name !== "AbortError") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "⚠️ Error processing voice turn through local Saki brain." }
        ]);
      }
      setSakiState("ERROR");
      setSakiActivity("Voice turn error.");
    } finally {
      setIsTyping(false);
      abortControllerRef.current = null;
    }
  }, [activeConvId, appSettings.tts_voice, appSettings.voice_speed, refreshSystemData]);

  const sendMessage = useCallback(async (text: string, attachments: ChatAttachment[] = [], languageMode: string = "AUTO") => {
    if (!text.trim() && attachments.length === 0) return;

    setLastTranscript(text);
    const userTurn: Message = { role: "user", content: text, attachments };
    setMessages((prev) => [...prev, userTurn]);
    setIsTyping(true);

    const hasImages = attachments.some(a => a.type?.startsWith("image/") || a.name?.match(/\.(png|jpg|jpeg|webp)$/i));
    setSakiState(hasImages ? "VISION" : "PROCESSING");
    setSakiActivity(hasImages ? "Inspecting attached visual artifact..." : "Reasoning and drafting response...");

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    let accumulatedText = "";

    try {
      await streamChat(
        text,
        attachments,
        (token) => {
          accumulatedText += token;
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: updated[lastIdx].content + token
              };
            }
            return updated;
          });
        },
        controller.signal,
        activeConvId,
        (event: SakiEvent) => {
          if (event.state) setSakiState(event.state);
          if (event.activity) setSakiActivity(event.activity);
          if (event.detected_language) setDetectedLanguage(event.detected_language);
          if (event.selected_model) {
            setDiagnostics((prev) => ({
              stage: event.state || "STREAMING",
              model: event.selected_model || prev?.model,
              mode: event.task || prev?.mode
            }));
          }
        },
        languageMode
      );

      const elapsed = typeof performance !== "undefined" ? Math.round(performance.now() - t0) : 0;
      setDiagnostics((prev) => ({
        stage: "COMPLETE",
        llmMs: elapsed,
        totalMs: elapsed,
        model: prev?.model || brainStatus?.model || "phi3:latest",
        task: prev?.task || "chat",
        mode: prev?.mode || "casual"
      }));

      if (accumulatedText.trim()) {
        setLastResponse(accumulatedText.trim());
      }

      // If voice mode is active or user requested speech, speak the response
      if (isVoiceActive && accumulatedText.trim()) {
        try {
          const speechBlob = await fetchSpeechAudio(
            accumulatedText,
            appSettings.tts_voice || "af_heart",
            appSettings.voice_speed || 1.0,
            controller.signal
          );
          if (speechBlob) {
            setSakiState("SPEAKING");
            setSakiActivity(`Saki speaking (${appSettings.tts_voice || "af_heart"})...`);
            await SakiVoicePlayer.getInstance().playSpeech(
              speechBlob,
              () => {
                setSakiState("IDLE");
                setSakiActivity("Turn complete.");
              }
            );
          }
        } catch (e) {
          console.warn("TTS playback failed:", e);
        }
      }

      setIsTyping(false);
      setSakiState("IDLE");
      setSakiActivity("Turn complete. Ready for next query.");
      refreshSystemData();
    } catch (err: unknown) {
      if ((err as Error)?.name !== "AbortError") {
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: "assistant", content: "Connection error communicating with local Saki service." }
        ]);
      }
      setIsTyping(false);
      setSakiState("ERROR");
    } finally {
      abortControllerRef.current = null;
    }
  }, [activeConvId, appSettings.tts_voice, appSettings.voice_speed, isVoiceActive, brainStatus?.model, refreshSystemData]);

  const handleRetry = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      sendMessage(lastUserMsg.content, lastUserMsg.attachments || []);
    }
  };

  return (
    <div 
      className={`flex h-screen w-screen overflow-hidden font-sans relative select-none transition-colors duration-700 ${
        isNight ? "text-slate-100" : "text-slate-900"
      }`}
      data-theme={appSettings.theme}
      suppressHydrationWarning
    >
      {/* ========================================================================= */}
      {/* PRIMARY VIEW 1: SAKI CORE PAGE (Dedicated Pure Black Experience)          */}
      {/* ========================================================================= */}
      {activeView === "core" ? (
        <SakiCorePage
          sakiState={sakiState}
          sakiActivity={sakiActivity}
          detectedLanguage={detectedLanguage}
          appSettings={appSettings}
          brainStatus={brainStatus}
          activeProject={userMemory?.awareness?.current_project}
          activeModel={diagnostics?.model || brainStatus?.model || "phi3:latest"}
          conversationMode={diagnostics?.mode || userMemory?.awareness?.conversation_mode || "casual"}
          userMood={userMemory?.awareness?.emotional_state?.emotion || "receptive"}
          isVoiceActive={isVoiceActive}
          onToggleVoice={handleToggleVoice}
          onVoiceTurn={sendVoiceTurn}
          onInterrupt={handleStop}
          onSwitchToChat={() => setActiveView("chat")}
          onOpenBrain={() => setIsBrainOpen(true)}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenMemory={() => setIsMemoryOpen(true)}
          lastTranscript={lastTranscript}
          lastResponse={lastResponse}
        />
      ) : (
        /* ======================================================================= */
        /* PRIMARY VIEW 2: CHAT PAGE (Everyday Workspace, Clear Sky & Dark Themes)  */
        /* ======================================================================= */
        <>
          {/* Dynamic Multi-Layered Environment Subsystem (Sprint 13) */}
          <SkyBackground
            theme={appSettings.theme}
            reducedMotion={appSettings.reduced_animation}
          />

          {/* Main 3-Zone Workstation Layout */}
          <div className="flex h-full w-full overflow-hidden relative z-10">
            
            {/* Zone 1: Left Navigation & Control Panel */}
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
              onToggleVoice={handleToggleVoice}
              isVoiceActive={isVoiceActive}
              activeProject={userMemory?.awareness?.current_project}
              theme={appSettings.theme}
              activeView={activeView}
              onSelectView={setActiveView}
            />

            {/* Zone 2: Central Everyday Conversation Stage (No Core in Background) */}
            <div className="flex-1 flex flex-col h-full overflow-hidden relative">
              
              {/* Top Bar HUD */}
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
                sakiState={sakiState}
                sakiActivity={sakiActivity}
                detectedLanguage={detectedLanguage}
                isVoiceActive={isVoiceActive}
                onToggleVoice={handleToggleVoice}
                activeView={activeView}
                onSelectView={setActiveView}
              />

              {/* Conversation Stream */}
              <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-3.5 z-1 pb-36 scroll-smooth">
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

                  {/* Empty Chat Starter Chips */}
                  {messages.length <= 1 && (
                    <div className="pt-6 pb-2 space-y-3 animate-slide-up">
                      <div className={`hud-label text-center text-[10px] ${isNight ? "text-cyan-400/80" : "text-sky-800 font-bold"}`}>
                        Quick Operational Inquiries
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {[
                          { icon: "⚡", title: "Analyze Codebase", query: "Can you inspect the active workspace architecture and summarize module interfaces?" },
                          { icon: "🎙️", title: "Real-Time Voice Test", query: "Let's test voice synthesis and real-time interruption pipeline." },
                          { icon: "🧠", title: "Memory & Cognitive State", query: "What projects and user preferences do you currently retain in your memory vault?" },
                          { icon: "🌐", title: "Atmosphere & Theme", query: "How does Clear Sky render procedural drifting clouds and light glassmorphism?" },
                        ].map((item, idx) => (
                          <button
                            key={idx}
                            onClick={() => sendMessage(item.query, [])}
                            className={`p-3 rounded-xl hud-card border text-left transition group ${
                              isNight
                                ? "border-cyan-500/20 hover:border-cyan-400/50"
                                : "border-sky-300 hover:border-sky-500 hover:shadow-md bg-white/75"
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm">{item.icon}</span>
                              <span className={`text-xs font-bold transition ${isNight ? "text-slate-200 group-hover:text-cyan-300" : "text-slate-900 group-hover:text-sky-800"}`}>
                                {item.title}
                              </span>
                            </div>
                            <p className={`text-[11px] truncate font-mono ${isNight ? "text-slate-400" : "text-slate-600"}`}>
                              {item.query}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Streaming Typing Indicator */}
                  {isTyping && (
                    <div className="flex w-full mb-3 justify-start animate-slide-up">
                      <div className={`px-4 py-2.5 rounded-2xl rounded-tl-xs flex items-center gap-2.5 border backdrop-blur-md shadow-lg ${
                        isNight 
                          ? "border-cyan-500/30 bg-slate-950/80 shadow-[0_0_15px_rgba(56,189,248,0.2)]" 
                          : "border-sky-300/80 bg-white/90 shadow-[0_4px_20px_rgba(14,165,233,0.15)]"
                      }`}>
                        <div className="flex gap-1">
                          <span className={`animate-bounce inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-500"}`} />
                          <span className={`animate-bounce inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-500"}`} style={{ animationDelay: '0.2s' }} />
                          <span className={`animate-bounce inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-500"}`} style={{ animationDelay: '0.4s' }} />
                        </div>
                        <span className={`text-[11px] font-mono animate-pulse ${isNight ? "text-cyan-300" : "text-sky-800 font-semibold"}`}>
                          Saki is synthesizing response...
                        </span>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </main>

              {/* Bottom Floating Command Dock */}
              <footer className={`absolute bottom-0 left-0 right-0 p-4 z-10 pointer-events-auto bg-gradient-to-t ${
                isNight 
                  ? "from-[#0a0e1a]/95 via-[#0a0e1a]/70 to-transparent" 
                  : "from-sky-100/90 via-sky-100/60 to-transparent"
              }`}>
                <div className="max-w-3xl w-full mx-auto">
                  {/* Live Diagnostic Telemetry Bar */}
                  {diagnostics && (
                    <div className={`flex items-center justify-between mb-2 px-3 py-1.5 rounded-xl border text-[11px] font-mono backdrop-blur-md animate-slide-up shadow-sm ${
                      isNight
                        ? "bg-slate-950/85 border-cyan-500/30 text-slate-300 shadow-[0_0_12px_rgba(56,189,248,0.15)]"
                        : "bg-white/95 border-sky-300 text-sky-900 shadow-sm"
                    }`}>
                      <div className="flex items-center gap-2">
                        <span className="text-cyan-400 font-bold">⚡ SAKI BRAIN:</span>
                        <span className="font-semibold text-slate-100">{diagnostics.model || "phi3:latest"}</span>
                        {diagnostics.mode && <span className="opacity-70">({diagnostics.mode})</span>}
                      </div>
                      <div className="flex items-center gap-3 text-xs opacity-90">
                        {diagnostics.sttMs !== undefined && <span>STT: <b className="text-emerald-400">{diagnostics.sttMs.toFixed(0)}ms</b></span>}
                        {diagnostics.llmMs !== undefined && <span>LLM: <b className="text-cyan-300">{diagnostics.llmMs.toFixed(0)}ms</b></span>}
                        {diagnostics.ttsMs !== undefined && <span>TTS: <b className="text-purple-300">{diagnostics.ttsMs.toFixed(0)}ms</b></span>}
                        {diagnostics.totalMs !== undefined && <span>TOTAL: <b className="text-amber-300">{diagnostics.totalMs.toFixed(0)}ms</b></span>}
                      </div>
                    </div>
                  )}

                  <InputBox 
                    onSend={sendMessage} 
                    onVoiceTurn={sendVoiceTurn}
                    onStop={handleStop} 
                    isGenerating={isTyping} 
                    isVoiceActive={isVoiceActive}
                    theme={appSettings.theme}
                  />
                </div>
              </footer>
            </div>

            {/* Zone 3: Right Saki Brain & Telemetry HUD Panel */}
            <BrainPanel
              isOpen={isBrainOpen}
              onClose={() => setIsBrainOpen(false)}
              brainStatus={brainStatus}
              theme={appSettings.theme}
              sakiState={sakiState}
              sakiActivity={sakiActivity}
              detectedLanguage={detectedLanguage}
            />
          </div>
        </>
      )}

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
        onPreviewState={(st) => {
          setSakiState(st);
          setSakiActivity(`Previewing ${st} state`);
        }}
      />
    </div>
  );
}
