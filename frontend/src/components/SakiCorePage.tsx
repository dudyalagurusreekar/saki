"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import SakiCore from "./core/SakiCore";
import { SakiState, BrainStatusData, AppSettings } from "../lib/api";
import { AudioRecorder } from "./core/engine/AudioRecorder";

interface SakiCorePageProps {
  sakiState: SakiState;
  sakiActivity?: string;
  detectedLanguage?: string | null;
  appSettings: AppSettings;
  brainStatus: BrainStatusData | null;
  activeProject?: string;
  activeModel?: string;
  conversationMode?: string;
  userMood?: string;
  onSelectModel?: (model: string) => void;
  isVoiceActive: boolean;
  onToggleVoice: () => void;
  onVoiceTurn?: (audioBlob: Blob, audioBase64: string) => void;
  onInterrupt?: () => void;
  onSwitchToChat: () => void;
  onOpenBrain: () => void;
  onOpenSettings: () => void;
  onOpenMemory: () => void;
  lastTranscript?: string;
  lastResponse?: string;
}

export default function SakiCorePage({
  sakiState = "IDLE",
  sakiActivity,
  detectedLanguage = "en",
  appSettings,
  brainStatus,
  activeProject,
  activeModel = "phi3:latest",
  conversationMode = "casual",
  userMood = "receptive",
  onSelectModel,
  isVoiceActive = false,
  onToggleVoice,
  onVoiceTurn,
  onInterrupt,
  onSwitchToChat,
  onOpenBrain,
  onOpenSettings,
  onOpenMemory,
  lastTranscript,
  lastResponse
}: SakiCorePageProps) {
  const [showCompactTelemetry, setShowCompactTelemetry] = useState(true);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [isContinuousSession, setIsContinuousSession] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [micVolume, setMicVolume] = useState(0);
  const [micError, setMicError] = useState<string | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);

  useEffect(() => {
    return () => {
      if (recorderRef.current) {
        recorderRef.current.cleanup();
      }
    };
  }, []);

  const startListening = useCallback(async () => {
    if (recorderRef.current?.getIsRecording()) return;
    setMicError(null);
    try {
      const recorder = new AudioRecorder({
        sampleRate: 16000,
        enableAutoSubmit: true,
        onVolumeChange: (vol) => setMicVolume(vol),
        onUtteranceFinalized: (payload) => {
          setIsRecording(false);
          setMicVolume(0);
          recorder.markSendVoiceTurnCalled();
          if (onVoiceTurn && payload.blob.size > 0) {
            onVoiceTurn(payload.blob, payload.base64);
          }
        },
        onError: (err) => {
          console.warn("[SakiCorePage Voice Error]:", err);
          setMicError(err.message);
          setIsRecording(false);
          setMicVolume(0);
        }
      });
      recorderRef.current = recorder;
      await recorder.start();
      setIsRecording(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Microphone access denied.";
      setMicError(msg);
      setIsRecording(false);
      setMicVolume(0);
    }
  }, [onVoiceTurn]);

  // Continuous conversational loop: Automatically re-arm microphone and listen whenever Saki finishes speaking
  useEffect(() => {
    if (!isContinuousSession) return;

    if ((sakiState === "IDLE" || sakiState === "LISTENING") && !isRecording) {
      const timer = setTimeout(() => {
        if (!recorderRef.current?.getIsRecording()) {
          startListening();
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [sakiState, isContinuousSession, isRecording, startListening]);

  const handleStartSession = async () => {
    setIsContinuousSession(true);
    await startListening();
  };

  const handleEndSession = () => {
    setIsContinuousSession(false);
    if (recorderRef.current) {
      recorderRef.current.cleanup();
      recorderRef.current = null;
    }
    setIsRecording(false);
    setMicVolume(0);
    onInterrupt?.();
  };

  const handleMicClick = async () => {
    setMicError(null);

    // If currently recording: stop and submit turn immediately
    if (isRecording && recorderRef.current) {
      await recorderRef.current.finalizeCurrentUtterance();
      return;
    }

    // If currently speaking: interrupt playback immediately (< 10ms) and begin listening
    if (sakiState === "SPEAKING") {
      onInterrupt?.();
      await startListening();
      return;
    }

    // Otherwise: begin listening
    await startListening();
  };

  // Status mapping
  const getStateMeta = (state: SakiState) => {
    switch (state) {
      case "LISTENING":
        return {
          icon: "🎙️",
          label: "LISTENING",
          color: "text-emerald-400 border-emerald-500/50 bg-emerald-950/60 shadow-[0_0_20px_rgba(16,185,129,0.35)]",
          dot: "bg-emerald-400 animate-ping",
          desc: sakiActivity || "Microphone armed (VAD active)..."
        };
      case "PROCESSING":
        return {
          icon: "⚙️",
          label: "PROCESSING",
          color: "text-amber-400 border-amber-500/50 bg-amber-950/60 shadow-[0_0_20px_rgba(245,158,11,0.35)]",
          dot: "bg-amber-400 animate-pulse",
          desc: sakiActivity || "Faster-Whisper transcribing speech..."
        };
      case "THINKING":
        return {
          icon: "🧠",
          label: "THINKING",
          color: "text-yellow-400 border-yellow-500/50 bg-yellow-950/60 shadow-[0_0_25px_rgba(234,179,8,0.4)]",
          dot: "bg-yellow-400 animate-pulse",
          desc: sakiActivity || "Neural matrix reasoning..."
        };
      case "SPEAKING":
        return {
          icon: "🔊",
          label: "SPEAKING",
          color: "text-rose-400 border-rose-500/60 bg-rose-950/70 shadow-[0_0_30px_rgba(244,63,94,0.45)]",
          dot: "bg-rose-400 animate-ping",
          desc: sakiActivity || "Harmonic speech synthesis active..."
        };
      case "SEARCHING":
        return {
          icon: "🌐",
          label: "SEARCHING",
          color: "text-blue-400 border-blue-500/50 bg-blue-950/60 shadow-[0_0_20px_rgba(59,130,246,0.35)]",
          dot: "bg-blue-400 animate-ping",
          desc: sakiActivity || "Directional radar & knowledge search..."
        };
      case "VISION":
        return {
          icon: "👁️",
          label: "VISION",
          color: "text-purple-400 border-purple-500/50 bg-purple-950/60 shadow-[0_0_25px_rgba(168,85,247,0.4)]",
          dot: "bg-purple-400 animate-pulse",
          desc: sakiActivity || "Multimodal visual inspection active..."
        };
      case "REMEMBERING":
        return {
          icon: "💾",
          label: "RECALLING",
          color: "text-teal-400 border-teal-500/50 bg-teal-950/60 shadow-[0_0_20px_rgba(20,184,166,0.35)]",
          dot: "bg-teal-400 animate-pulse",
          desc: sakiActivity || "Cross-lingual memory retrieval..."
        };
      case "ACTING":
        return {
          icon: "⚡",
          label: "ACTING",
          color: "text-orange-400 border-orange-500/50 bg-orange-950/60 shadow-[0_0_25px_rgba(249,115,22,0.4)]",
          dot: "bg-orange-400 animate-ping",
          desc: sakiActivity || "Executing capability..."
        };
      case "ERROR":
        return {
          icon: "⚠️",
          label: "ERROR",
          color: "text-red-400 border-red-500/60 bg-red-950/80 shadow-[0_0_25px_rgba(239,68,68,0.4)]",
          dot: "bg-red-400",
          desc: sakiActivity || "Controlled recovery active..."
        };
      case "IDLE":
      default:
        return {
          icon: "◇",
          label: "STANDBY",
          color: "text-slate-200 border-slate-700/60 bg-slate-900/60 shadow-[0_0_15px_rgba(255,255,255,0.1)]",
          dot: "bg-slate-300",
          desc: sakiActivity || "Serene baseline orbit ready."
        };
    }
  };

  const stateMeta = getStateMeta(sakiState);

  // Model Metadata and Mood-driven capability descriptors
  const getModelMeta = (modelKey: string) => {
    const m = (modelKey || "").toLowerCase();
    if (m.includes("hermes")) {
      return {
        id: "nous-hermes2:latest",
        name: "Hermes 2",
        role: "❤️ Support & Mood",
        desc: "Empathetic understanding & emotional presence",
        color: "text-rose-300 border-rose-500/50 bg-rose-950/60 shadow-[0_0_15px_rgba(244,63,94,0.3)]",
        dot: "bg-rose-400"
      };
    }
    if (m.includes("coder")) {
      return {
        id: "qwen2.5-coder:7b",
        name: "Qwen Coder",
        role: "💻 Builder / Code",
        desc: "Software engineering & repo diagnostics",
        color: "text-amber-300 border-amber-500/50 bg-amber-950/60 shadow-[0_0_15px_rgba(245,158,11,0.3)]",
        dot: "bg-amber-400"
      };
    }
    if (m.includes("qwen")) {
      return {
        id: "qwen3:8b",
        name: "Qwen 3",
        role: "🧠 Deep Thinking",
        desc: "Structured analytical reasoning & logic",
        color: "text-indigo-300 border-indigo-500/50 bg-indigo-950/60 shadow-[0_0_15px_rgba(99,102,241,0.3)]",
        dot: "bg-indigo-400"
      };
    }
    if (m.includes("gemma")) {
      return {
        id: "gemma3:4b",
        name: "Gemma 3",
        role: "👁️ Vision",
        desc: "Multimodal visual inspection & OCR",
        color: "text-purple-300 border-purple-500/50 bg-purple-950/60 shadow-[0_0_15px_rgba(168,85,247,0.3)]",
        dot: "bg-purple-400"
      };
    }
    return {
      id: "phi3:latest",
      name: "Phi-3",
      role: "⚡ Casual / Speed",
      desc: "Fast, natural conversational dialogue",
      color: "text-cyan-300 border-cyan-500/50 bg-cyan-950/60 shadow-[0_0_15px_rgba(56,189,248,0.3)]",
      dot: "bg-cyan-400"
    };
  };

  const currentModelMeta = getModelMeta(activeModel || brainStatus?.model || "phi3:latest");

  const getMoodLabel = (mood?: string, mode?: string) => {
    const md = (mode || "").toLowerCase();
    const m = (mood || "").toLowerCase();
    if (md === "support" || m.includes("sad") || m.includes("lonely") || m.includes("discouraged")) {
      return { label: "❤️ Empathetic Presence", color: "text-rose-300 bg-rose-950/50 border-rose-500/30" };
    }
    if (md === "builder" || m.includes("frustrated") || m.includes("tired")) {
      return { label: "⚡ Focused Resolution", color: "text-amber-300 bg-amber-950/50 border-amber-500/30" };
    }
    if (m.includes("celebrating")) {
      return { label: "🎉 Breakthrough Win", color: "text-emerald-300 bg-emerald-950/50 border-emerald-500/30" };
    }
    if (md === "thinking") {
      return { label: "🧠 Deep Exploration", color: "text-indigo-300 bg-indigo-950/50 border-indigo-500/30" };
    }
    return { label: "✨ Receptive & Grounded", color: "text-cyan-300 bg-cyan-950/50 border-cyan-500/30" };
  };

  const currentMoodMeta = getMoodLabel(userMood, conversationMode);

  const getLanguageLabel = (lang?: string | null) => {
    if (!lang) return "English (EN)";
    const l = lang.toLowerCase();
    if (l === "te" || l === "telugu") return "తెలుగు (TE)";
    if (l === "kn" || l === "kannada") return "ಕನ್ನಡ (KN)";
    if (l.includes("te") && l.includes("en")) return "తెలుగు + English";
    if (l.includes("kn") && l.includes("en")) return "ಕನ್ನಡ + English";
    return "English (EN)";
  };

  const AVAILABLE_MODELS = [
    { id: "phi3:latest", name: "Phi-3", role: "⚡ Casual / Speed", desc: "Fast everyday dialogue" },
    { id: "nous-hermes2:latest", name: "Hermes 2", role: "❤️ Support & Mood", desc: "Emotional validation & presence" },
    { id: "qwen2.5-coder:7b", name: "Qwen Coder", role: "💻 Builder / Code", desc: "Software & repo debugging" },
    { id: "qwen3:8b", name: "Qwen 3", role: "🧠 Deep Thinking", desc: "Complex reasoning & logic" },
    { id: "gemma3:4b", name: "Gemma 3", role: "👁️ Vision", desc: "Image analysis & OCR" }
  ];

  return (
    <div 
      className="relative w-screen h-screen bg-black text-slate-100 overflow-hidden select-none font-sans flex flex-col justify-between"
      style={{ backgroundColor: "#000000" }}
    >
      {/* 1. TOP FLOATING NAVIGATION & HUD BAR */}
      <header className="relative z-30 flex items-center justify-between px-4 py-3.5 md:px-8 bg-gradient-to-b from-black/90 via-black/50 to-transparent">
        {/* Left: Navigation Switcher (Chat vs Core) */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950/80 border border-cyan-500/30 rounded-xl p-1 shadow-[0_0_15px_rgba(56,189,248,0.15)] backdrop-blur-md">
            <button
              onClick={onSwitchToChat}
              className="px-3.5 py-1.5 rounded-lg font-mono text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800/80 transition flex items-center gap-1.5"
              title="Switch to Full Chat Workspace"
            >
              <span>💬</span>
              <span>Chat</span>
            </button>
            <button
              className="px-3.5 py-1.5 rounded-lg font-mono text-xs font-bold text-cyan-300 bg-cyan-950/70 border border-cyan-500/40 shadow-[0_0_10px_rgba(56,189,248,0.3)] transition flex items-center gap-1.5"
              title="Active: Saki Core Experience"
            >
              <span>⚛️</span>
              <span>Saki Core</span>
            </button>

            {onToggleVoice && (
              <button
                type="button"
                onClick={onToggleVoice}
                className={`px-2.5 py-1.5 rounded-lg font-mono text-[11px] font-bold transition flex items-center gap-1.5 ${
                  isVoiceActive
                    ? "bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 shadow-[0_0_8px_rgba(16,185,129,0.3)]"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title={isVoiceActive ? "Voice is Armed / Active" : "Voice is Inactive"}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${isVoiceActive ? "bg-emerald-400 animate-ping" : "bg-slate-500"}`} />
                <span>{isVoiceActive ? "VOICE" : "MUTED"}</span>
              </button>
            )}
          </div>

          {/* Live Dynamic Model & Mood Swapping Button */}
          <div className="relative">
            <button
              onClick={() => setShowModelPicker(prev => !prev)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border backdrop-blur-md font-mono text-xs transition-all ${currentModelMeta.color}`}
              title="Dynamic Model Swapper: Swaps according to mood & posture"
            >
              <span className={`w-2 h-2 rounded-full ${currentModelMeta.dot}`} />
              <span className="font-bold">{currentModelMeta.name}</span>
              <span className="text-[10px] text-slate-300 opacity-80">({currentModelMeta.role})</span>
              <span className="text-[9px] text-slate-400">▾</span>
            </button>

            {/* Model Swapper Dropdown */}
            {showModelPicker && (
              <div className="absolute top-10 left-0 z-50 w-64 p-2 rounded-2xl bg-slate-950/95 border border-cyan-500/40 shadow-[0_0_30px_rgba(0,0,0,0.8)] backdrop-blur-xl flex flex-col gap-1 font-mono text-xs animate-in fade-in zoom-in-95 duration-150">
                <div className="px-2.5 py-1.5 text-[10px] text-cyan-400 font-bold border-b border-slate-800 flex justify-between">
                  <span>SWAP MODEL BY MOOD / CAPABILITY</span>
                  <span>⚡ AUTO</span>
                </div>
                {AVAILABLE_MODELS.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      onSelectModel?.(m.id);
                      setShowModelPicker(false);
                    }}
                    className={`flex flex-col text-left px-2.5 py-2 rounded-xl transition ${
                      currentModelMeta.id === m.id
                        ? "bg-cyan-950/80 border border-cyan-500/50 text-cyan-200"
                        : "hover:bg-slate-900/80 text-slate-300 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold">{m.name}</span>
                      <span className="text-[10px] text-slate-400">{m.role}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-0.5">{m.desc}</span>
                  </button>
                ))}
              </div>
            )}
            {/* Active Project Pill */}
            {activeProject && (
              <div className="hidden xl:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-cyan-500/20 bg-slate-950/70 text-slate-300 font-mono text-xs">
                <span className="text-cyan-400">📁</span>
                <span className="font-semibold text-cyan-200">{activeProject}</span>
              </div>
            )}
          </div>
        </div>

        {/* Center: Live Status & Activity Indicator */}
        <div className="flex items-center gap-2.5 px-4 py-1.5 rounded-full border backdrop-blur-md transition-all duration-300 font-mono text-xs font-semibold shadow-lg">
          <span className={`w-2.5 h-2.5 rounded-full ${stateMeta.dot}`} />
          <span className="text-slate-400 text-[10px] uppercase tracking-wider">{stateMeta.label}</span>
          <span className="text-slate-300 font-normal hidden sm:inline">• {stateMeta.desc}</span>
        </div>

        {/* Right: Telemetry & Tools */}
        <div className="flex items-center gap-2.5">
          {/* Detected Language Pill */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-xl border border-slate-800 bg-slate-950/60 text-slate-300 text-xs font-mono">
            <span className="text-[10px] text-cyan-400">LANG:</span>
            <span className="font-semibold text-cyan-200">{getLanguageLabel(detectedLanguage)}</span>
          </div>

          {/* Quick HUD controls */}
          <button
            onClick={() => setShowCompactTelemetry(prev => !prev)}
            className={`p-2 rounded-xl border transition text-xs font-mono ${
              showCompactTelemetry 
                ? "border-cyan-500/40 bg-cyan-950/60 text-cyan-300" 
                : "border-slate-800 bg-slate-950/40 text-slate-400 hover:text-white"
            }`}
            title="Toggle compact telemetry HUD"
          >
            <span>📊</span>
          </button>

          <button
            onClick={onOpenMemory}
            className="p-2 rounded-xl border border-slate-800 bg-slate-950/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/40 transition text-xs"
            title="Open Memory Vault"
          >
            <span>💾</span>
          </button>

          <button
            onClick={onOpenBrain}
            className="p-2 rounded-xl border border-slate-800 bg-slate-950/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/40 transition text-xs"
            title="Open Brain Diagnostics"
          >
            <span>🧠</span>
          </button>

          <button
            onClick={onOpenSettings}
            className="p-2 rounded-xl border border-slate-800 bg-slate-950/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/40 transition text-xs"
            title="Open System Settings"
          >
            <span>⚙️</span>
          </button>
        </div>
      </header>

      {/* 2. MAIN VIEWPORT — ANIMATED 3D SAKI CORE */}
      <main className="relative flex-1 w-full h-full flex items-center justify-center overflow-hidden">
        {/* Full Viewport 3D Energy Core */}
        <div className="absolute inset-0 flex items-center justify-center">
          <SakiCore
            state={isRecording ? "LISTENING" : sakiState}
            activity={isRecording ? "Listening to your voice..." : sakiActivity}
            theme="night_sky"
            quality={appSettings.core_quality || "high"}
            opacity={appSettings.core_opacity ?? 1.0}
            scale={1.35}
            reducedMotion={appSettings.reduced_animation}
            showHudTelemetry={appSettings.core_show_hud !== false}
            audioSensitivity={appSettings.audio_sensitivity || 1.2}
            className="w-full h-full max-w-[1200px] max-h-[1200px]"
          />
        </div>

        {/* Compact Supporting Telemetry Overlays (Top-Left & Top-Right of Core) */}
        {showCompactTelemetry && (
          <>
            {/* Top-Left: Dynamic Model & Mood/Posture Awareness */}
            <div className="absolute top-4 left-6 z-20 hidden md:flex flex-col gap-1.5 p-3 rounded-2xl border border-cyan-500/20 bg-slate-950/80 backdrop-blur-md font-mono text-[10px] shadow-xl">
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>ACTIVE MODEL:</span>
                <span className="font-bold text-cyan-300">{currentModelMeta.name} ({currentModelMeta.role})</span>
              </div>
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>MOOD & POSTURE:</span>
                <span className={`px-2 py-0.5 rounded-md border text-[9px] font-bold ${currentMoodMeta.color}`}>
                  {currentMoodMeta.label}
                </span>
              </div>
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>CONVERSATION MODE:</span>
                <span className="font-bold uppercase text-slate-200">{conversationMode}</span>
              </div>
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>TURN LATENCY:</span>
                <span className="font-bold text-emerald-400">
                  {brainStatus?.latency_ms ? `${brainStatus.latency_ms.toFixed(0)} ms` : "0 ms"}
                </span>
              </div>
            </div>

            {/* Top-Right: Hardware Resource Metrics */}
            <div className="absolute top-4 right-6 z-20 hidden md:flex flex-col gap-1.5 p-3 rounded-2xl border border-cyan-500/20 bg-slate-950/80 backdrop-blur-md font-mono text-[10px] shadow-xl pointer-events-none">
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>HOST RAM:</span>
                <span className="font-bold text-cyan-300">{brainStatus?.ram_usage || "Unavailable"}</span>
              </div>
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>COMPUTE GPU:</span>
                <span className="font-bold text-slate-200 truncate max-w-[140px]">{brainStatus?.gpu_name || "CPU / Shared RAM"}</span>
              </div>
              <div className="flex justify-between items-center gap-4 text-slate-400">
                <span>DURABLE MEMORY:</span>
                <span className="font-bold text-teal-300">{brainStatus?.memory_count ?? 0} items</span>
              </div>
            </div>
          </>
        )}

        {/* Live Audio Volume VU Meter when Recording */}
        {isRecording && (
          <div className="absolute bottom-28 z-25 flex flex-col items-center gap-1.5 px-5 py-2.5 rounded-2xl bg-slate-950/90 border border-emerald-500/50 shadow-[0_0_25px_rgba(16,185,129,0.3)] backdrop-blur-md animate-in fade-in zoom-in-95 duration-150 font-mono text-[10px]">
            <div className="flex items-center gap-2 text-emerald-400">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="font-bold tracking-wider">LISTENING (VAD ACTIVE)</span>
            </div>
            {/* Live Volume Level Bar */}
            <div className="w-36 h-2 rounded-full bg-slate-800/80 overflow-hidden p-0.5 border border-emerald-500/20">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-300 transition-all duration-75"
                style={{ width: `${Math.min(100, Math.max(8, micVolume * 250))}%` }}
              />
            </div>
          </div>
        )}

        {/* Neural Thinking / Reasoning State HUD */}
        {!isRecording && (sakiState === "THINKING" || sakiState === "PROCESSING" || sakiState === "SEARCHING" || sakiState === "VISION" || sakiState === "REMEMBERING" || sakiState === "ACTING") && (
          <div className="absolute bottom-28 z-25 max-w-xl px-6 py-3.5 rounded-2xl bg-slate-950/90 border border-violet-500/50 text-violet-200 text-xs font-mono shadow-[0_0_30px_rgba(168,85,247,0.3)] backdrop-blur-md animate-in fade-in slide-in-from-bottom-3 duration-200 flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-violet-500"></span>
            </span>
            <div className="flex flex-col">
              <span className="text-[10px] text-violet-400 uppercase font-bold tracking-widest">
                NEURAL MATRIX // {sakiState}
              </span>
              <span className="text-slate-200 text-xs">
                {sakiActivity || "Synthesizing response through specialist model..."}
              </span>
            </div>
          </div>
        )}

        {/* Saki Response Output HUD (When Speaking or Recent Turn Complete) */}
        {!isRecording && (sakiState === "SPEAKING" || lastResponse) && (sakiState !== "THINKING" && sakiState !== "PROCESSING") && (
          <div className="absolute bottom-28 z-25 max-w-2xl w-[90%] md:w-auto px-6 py-4 rounded-2xl bg-slate-950/95 border border-cyan-500/40 text-slate-100 shadow-[0_0_35px_rgba(56,189,248,0.25)] backdrop-blur-xl animate-in fade-in slide-in-from-bottom-3 duration-200 flex flex-col gap-2 max-h-48 overflow-y-auto">
            <div className="flex items-center justify-between text-[10px] font-mono border-b border-cyan-500/20 pb-1.5">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${sakiState === "SPEAKING" ? "bg-pink-400 animate-ping" : "bg-cyan-400"}`} />
                <span className="text-cyan-300 font-bold tracking-widest uppercase">
                  {sakiState === "SPEAKING" ? "SAKI // SPEAKING" : "SAKI // RESPONSE"}
                </span>
                {detectedLanguage && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
                    {detectedLanguage.toUpperCase()}
                  </span>
                )}
              </div>
              <span className="text-slate-400 font-mono text-[10px]">{activeModel}</span>
            </div>
            {lastTranscript && (
              <div className="text-[11px] font-mono text-slate-400 truncate">
                <span className="text-cyan-500 mr-1">YOU &gt;</span> &ldquo;{lastTranscript}&rdquo;
              </div>
            )}
            <div className="text-slate-100 leading-relaxed font-sans text-xs select-text">
              {lastResponse}
            </div>
          </div>
        )}

        {/* User Transcript Subtitle fallback if no response yet */}
        {lastTranscript && !isRecording && !lastResponse && sakiState !== "THINKING" && sakiState !== "PROCESSING" && (
          <div className="absolute bottom-28 z-25 max-w-xl px-5 py-2.5 rounded-2xl bg-slate-950/85 border border-cyan-500/30 text-cyan-200 text-xs font-mono shadow-[0_0_25px_rgba(56,189,248,0.2)] backdrop-blur-md animate-in fade-in slide-in-from-bottom-2 duration-200 text-center">
            <span className="text-[10px] text-cyan-400 uppercase font-bold mr-2">TRANSCRIPT //</span>
            <span>&ldquo;{lastTranscript}&rdquo;</span>
          </div>
        )}

        {/* Mic Error Banner */}
        {micError && (
          <div className="absolute bottom-24 z-30 px-4 py-2 rounded-xl border border-red-500/40 bg-red-950/90 text-red-300 text-xs font-mono">
            <span>⚠️ {micError}</span>
          </div>
        )}
      </main>

      {/* 3. BOTTOM FLOATING INTERACTIVE VOICE CONTROLS */}
      <footer className="relative z-30 flex items-center justify-center p-6 bg-gradient-to-t from-black via-black/80 to-transparent">
        <div className="flex items-center gap-3 bg-slate-950/90 border border-cyan-500/30 rounded-2xl px-6 py-3 shadow-[0_0_30px_rgba(56,189,248,0.2)] backdrop-blur-md">
          {isContinuousSession ? (
            <>
              {/* Active Continuous Session Controls */}
              {sakiState === "SPEAKING" ? (
                <button
                  onClick={handleMicClick}
                  className="px-5 py-2.5 rounded-xl font-mono text-xs font-bold transition-all flex items-center gap-2.5 shadow-lg bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white shadow-[0_0_20px_rgba(244,63,94,0.5)] animate-pulse"
                  title="Interrupt speech & speak immediately (< 10ms)"
                >
                  <span className="w-2 h-2 rounded-xs bg-white animate-pulse" />
                  <span>BARGE-IN / SPEAK</span>
                </button>
              ) : isRecording ? (
                <button
                  onClick={handleMicClick}
                  className="px-5 py-2.5 rounded-xl font-mono text-xs font-bold transition-all flex items-center gap-2.5 shadow-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-[0_0_25px_rgba(16,185,129,0.5)] animate-pulse"
                  title="Finish speaking and send turn now"
                >
                  <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                  <span>DONE (TAP TO SEND)</span>
                </button>
              ) : (
                <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-950/60 border border-amber-500/40 font-mono text-xs text-amber-300">
                  <span className="animate-spin text-xs">⚙️</span>
                  <span>THINKING...</span>
                </div>
              )}

              {/* End Voice Session Button */}
              <button
                onClick={handleEndSession}
                className="px-4 py-2.5 rounded-xl border border-red-500/40 bg-red-950/80 hover:bg-red-900 font-mono text-xs font-bold text-red-200 hover:text-white transition flex items-center gap-1.5 shadow-md"
                title="Stop conversation and return Saki to Standby"
              >
                <span className="text-xs">⏹️</span>
                <span>END SESSION</span>
              </button>
            </>
          ) : (
            /* Standby: Start Continuous Conversation */
            <button
              onClick={handleStartSession}
              className="px-6 py-2.5 rounded-xl font-mono text-xs font-bold transition-all flex items-center gap-2.5 shadow-lg bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white shadow-[0_0_25px_rgba(20,184,166,0.4)]"
              title="Start hands-free continuous voice conversation with Saki Core"
            >
              <span className="text-sm">🎙️</span>
              <span>START CONVERSATION</span>
            </button>
          )}

          {/* Quick Switch to Chat Workspace Button */}
          <button
            onClick={onSwitchToChat}
            className="px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-900/80 hover:bg-slate-800 font-mono text-xs font-semibold text-slate-300 hover:text-white hover:border-cyan-500/40 transition flex items-center gap-2"
          >
            <span>💬</span>
            <span>Chat</span>
          </button>
        </div>
      </footer>
    </div>
  );
}
