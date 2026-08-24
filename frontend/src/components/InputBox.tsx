"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { uploadFile, ChatAttachment } from "../lib/api";
import { SakiTheme } from "../lib/theme";
import { AudioRecorder } from "./core/engine/AudioRecorder";

interface InputBoxProps {
  onSend: (text: string, attachments: ChatAttachment[], languageMode?: string) => void;
  onVoiceTurn?: (audioBlob: Blob, audioBase64: string) => void;
  onStop?: () => void;
  isGenerating?: boolean;
  isVoiceActive?: boolean;
  theme?: SakiTheme;
}

export default function InputBox({
  onSend,
  onVoiceTurn,
  onStop,
  isGenerating = false,
  isVoiceActive = false,
  theme = "night_sky"
}: InputBoxProps) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [languageMode, setLanguageMode] = useState<"AUTO" | "EN" | "TE" | "KN">("AUTO");
  const [isUploading, setIsUploading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [micVolume, setMicVolume] = useState(0);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<AudioRecorder | null>(null);
  const isNight = theme === "night_sky";

  // Cleanup recorder on unmount
  useEffect(() => {
    return () => {
      if (recorderRef.current) {
        recorderRef.current.cleanup();
      }
    };
  }, []);

  const handleSend = () => {
    if (isGenerating && onStop) {
      onStop();
      return;
    }

    if (input.trim() || attachments.length > 0) {
      onSend(input.trim(), attachments, languageMode);
      setInput("");
      setAttachments([]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !isGenerating) {
      handleSend();
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const file = files[0];
      const uploaded = await uploadFile(file);
      const ext = file.name.split('.').pop() || "";
      
      setAttachments((prev) => [
        ...prev,
        {
          name: uploaded.name,
          path: uploaded.path,
          type: ext.toUpperCase(),
          size: `${(file.size / (1024 * 1024)).toFixed(1)}MB`.replace(".0", "")
        }
      ]);
    } catch (err) {
      alert("Failed to upload attachment to Saki workspace");
      console.error(err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleVoiceToggle = async () => {
    setVoiceError(null);

    // If currently recording: Stop recording and send audio turn immediately
    if (isRecording) {
      try {
        if (recorderRef.current) {
          const { blob, base64 } = await recorderRef.current.stop();
          setIsRecording(false);
          setMicVolume(0);
          if (onVoiceTurn) {
            onVoiceTurn(blob, base64);
          }
        }
      } catch (err: unknown) {
        console.error("Failed to stop voice recording:", err);
        setIsRecording(false);
        setMicVolume(0);
      }
      return;
    }

    // Start recording from local browser microphone with instant dynamic conversational VAD
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
          console.warn("[InputBox Voice Error]:", err);
          setVoiceError(err.message);
          setIsRecording(false);
          setMicVolume(0);
        }
      });
      recorderRef.current = recorder;
      await recorder.start();
      setIsRecording(true);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Microphone access denied.";
      setVoiceError(errMsg);
      setIsRecording(false);
      setMicVolume(0);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      {/* Uploaded File Drawer Preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 px-1">
          {attachments.map((att, i) => (
            <div 
              key={i} 
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border font-mono animate-slide-up shadow-sm ${
                isNight
                  ? "bg-slate-900/90 text-cyan-200 border-cyan-500/30"
                  : "bg-white/95 text-sky-900 border-sky-300"
              }`}
            >
              <span className="text-[10px]">📎</span>
              <span className="truncate max-w-[150px] font-medium">{att.name}</span>
              <button 
                suppressHydrationWarning
                onClick={() => removeAttachment(i)} 
                className="text-slate-400 hover:text-rose-500 font-bold ml-1 transition"
                title="Remove file"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Non-intrusive Voice Error Toast */}
      {voiceError && (
        <div className="mb-2 px-3 py-1.5 rounded-lg border border-red-500/40 bg-red-950/80 text-red-300 text-xs font-mono flex items-center justify-between animate-slide-up">
          <span>⚠️ {voiceError}</span>
          <button onClick={() => setVoiceError(null)} className="ml-2 font-bold hover:text-white">✕</button>
        </div>
      )}

      {/* Main Command Dock */}
      <div className="relative flex items-center rounded-2xl cyber-input-dock hud-corner-bracket p-1.5 pl-3 transition-all duration-300">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept="image/*,.pdf,.txt,.py,.js,.ts,.json,.csv,.md"
        />

        {/* Attachment / Vision Trigger */}
        <button
          suppressHydrationWarning
          onClick={handleAttachClick}
          disabled={isUploading || isGenerating}
          className={`p-2 rounded-xl border border-transparent transition flex items-center justify-center disabled:opacity-30 flex-shrink-0 ${
            isNight
              ? "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60 hover:border-cyan-500/25"
              : "text-slate-500 hover:text-sky-800 hover:bg-sky-100/70 hover:border-sky-300"
          }`}
          title="Attach files or visual artifacts"
        >
          {isUploading ? (
            <div className="w-4 h-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          ) : (
            <span className="text-sm">📎</span>
          )}
        </button>

        {/* Voice Input Microphone Trigger (Connected to local Faster-Whisper + Kokoro TTS with 2s Silence VAD) */}
        <button
          suppressHydrationWarning
          onClick={handleVoiceToggle}
          disabled={isGenerating}
          className={`relative p-2 rounded-xl transition flex items-center justify-center disabled:opacity-30 flex-shrink-0 ml-0.5 ${
            isRecording 
              ? "bg-rose-950/90 text-rose-300 border border-rose-500/70 shadow-[0_0_20px_rgba(244,63,94,0.5)] animate-pulse" 
              : isVoiceActive
              ? "bg-teal-950/80 text-teal-300 border border-teal-500/50"
              : isNight
              ? "text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60 border border-transparent hover:border-cyan-500/25"
              : "text-slate-500 hover:text-sky-800 hover:bg-sky-100/70 border border-transparent hover:border-sky-300"
          }`}
          title={isRecording ? "Listening to microphone (tap to send immediately)" : "Start voice conversation"}
        >
          <span className="text-sm">{isRecording ? "🎙️" : "🎤"}</span>
          {/* Live volume amplitude ring */}
          {isRecording && (
            <span 
              className="absolute inset-0 rounded-xl border-2 border-rose-400 pointer-events-none transition-transform duration-75"
              style={{ transform: `scale(${1.0 + micVolume * 0.4})`, opacity: Math.max(0.4, micVolume) }}
            />
          )}
        </button>

        {/* Prompt Input Field */}
        <input
          suppressHydrationWarning
          type="text"
          placeholder={
            isGenerating 
              ? "Saki is synthesizing response... press Stop to cancel" 
              : isRecording 
                ? "Listening to your voice... (tap Send when finished)"
                : "Message Saki or speak naturally (English / Telugu / Kannada)..."
          }
          className={`flex-1 bg-transparent text-xs md:text-sm focus:outline-none ml-2 font-medium ${
            isNight 
              ? "text-slate-100 placeholder-slate-500" 
              : "text-slate-900 placeholder-slate-400 font-medium"
          }`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGenerating}
        />
        
        {/* Compact Language Mode Badge / Cycle Selector */}
        <button
          suppressHydrationWarning
          type="button"
          onClick={() => {
            const modes: Array<"AUTO" | "EN" | "TE" | "KN"> = ["AUTO", "EN", "TE", "KN"];
            const nextIdx = (modes.indexOf(languageMode) + 1) % modes.length;
            setLanguageMode(modes[nextIdx]);
          }}
          className={`px-2 py-1 rounded-lg border text-[10px] font-mono font-bold transition flex items-center gap-1 flex-shrink-0 ml-1 shadow-xs ${
            languageMode === "TE"
              ? isNight ? "bg-amber-950/80 text-amber-300 border-amber-500/60" : "bg-amber-100 text-amber-900 border-amber-400"
              : languageMode === "KN"
              ? isNight ? "bg-purple-950/80 text-purple-300 border-purple-500/60" : "bg-purple-100 text-purple-900 border-purple-400"
              : languageMode === "EN"
              ? isNight ? "bg-cyan-950/80 text-cyan-300 border-cyan-500/60" : "bg-sky-100 text-sky-900 border-sky-400"
              : isNight ? "bg-slate-800/60 text-slate-300 border-slate-700 hover:border-slate-500" : "bg-slate-100 text-slate-700 border-slate-300 hover:border-slate-400"
          }`}
          title={`Language Mode: ${languageMode} (click to cycle AUTO → EN → తెలుగు → ಕನ್ನಡ)`}
        >
          <span>🌐</span>
          <span>{languageMode === "TE" ? "తెలుగు" : languageMode === "KN" ? "ಕನ್ನಡ" : languageMode}</span>
        </button>

        {/* Send or Stop Action Button */}
        {isGenerating ? (
          <button
            suppressHydrationWarning
            onClick={onStop}
            className="ml-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-mono text-xs font-bold transition-all transform hover:scale-102 active:scale-98 shadow-[0_0_15px_rgba(244,63,94,0.4)] flex items-center gap-1.5 flex-shrink-0"
            title="Stop generation (<10ms cancellation)"
          >
            <span className="w-2 h-2 bg-white rounded-xs animate-pulse" />
            <span>STOP</span>
          </button>
        ) : isRecording ? (
          <button
            suppressHydrationWarning
            onClick={handleVoiceToggle}
            className="ml-2 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-mono text-xs font-bold transition-all shadow-md flex items-center gap-1.5 flex-shrink-0 animate-pulse"
            title="Finish speaking and send immediately"
          >
            <span>✓</span>
            <span>SEND</span>
          </button>
        ) : (
          <button
            suppressHydrationWarning
            onClick={handleSend}
            disabled={!input.trim() && attachments.length === 0}
            className="ml-2 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-mono text-xs font-bold transition-all transform hover:scale-102 active:scale-98 disabled:opacity-40 disabled:hover:scale-100 disabled:hover:from-cyan-600 disabled:hover:to-indigo-600 shadow-md flex items-center gap-1.5 flex-shrink-0"
            title="Send message (Enter)"
          >
            <span>SEND</span>
            <span className="text-[10px]">↵</span>
          </button>
        )}
      </div>
    </div>
  );
}
