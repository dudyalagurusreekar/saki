import { useState, useRef, KeyboardEvent } from "react";
import { uploadFile, ChatAttachment } from "../lib/api";

interface SpeechRecognitionEvent {
  results: Array<Array<{ transcript: string }>>;
}

interface SpeechRecognitionInstance {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onstart: () => void;
  onend: () => void;
  onerror: () => void;
  onresult: (event: SpeechRecognitionEvent) => void;
}

interface CustomWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionInstance;
  webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
}

interface InputBoxProps {
  onSend: (text: string, attachments: ChatAttachment[]) => void;
  onStop?: () => void;
  isGenerating?: boolean;
  theme?: "clear_sky" | "night_sky";
}

export default function InputBox({
  onSend,
  onStop,
  isGenerating = false,
  theme = "clear_sky"
}: InputBoxProps) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isNight = theme === "night_sky";

  const handleSend = () => {
    if (isGenerating && onStop) {
      onStop();
      return;
    }

    if (input.trim() || attachments.length > 0) {
      onSend(input.trim(), attachments);
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
      alert("Failed to upload attachment to backend");
      console.error(err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleVoiceToggle = () => {
    const customWin = typeof window !== "undefined" ? (window as CustomWindow) : null;
    const SpeechRecognitionClass = customWin?.SpeechRecognition || customWin?.webkitSpeechRecognition;
    
    if (!SpeechRecognitionClass) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);
      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      };

      recognition.start();
    } catch (err) {
      console.error("Speech recognition error:", err);
      setIsListening(false);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      {/* Attachments list */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 px-3">
          {attachments.map((att, i) => (
            <div 
              key={i} 
              className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full font-medium shadow-md backdrop-blur-md animate-slide-up border ${
                isNight 
                  ? "bg-slate-800/90 border-slate-700 text-slate-200" 
                  : "bg-white/90 border-slate-200 text-slate-700"
              }`}
            >
              <span className="bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-[9px] px-2 py-0.5 rounded-full font-bold">
                {att.type}
              </span>
              <span className="truncate max-w-[140px] font-semibold">{att.name}</span>
              <span className="text-[10px] opacity-60">({att.size})</span>
              <button onClick={() => removeAttachment(i)} className="text-slate-400 hover:text-red-500 font-bold ml-1 transition">×</button>
            </div>
          ))}
        </div>
      )}

      {/* Main Composer Box */}
      <div 
        className={`relative flex items-center rounded-full border shadow-xl p-1.5 pl-3.5 backdrop-blur-xl transition-all ${
          isNight 
            ? "bg-[#111827]/90 border-slate-700/80 shadow-[0_4px_25px_rgba(0,0,0,0.5)]" 
            : "bg-white/90 border-slate-200 shadow-[0_4px_25px_rgba(0,0,0,0.06)]"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Attachment button */}
        <button
          suppressHydrationWarning
          onClick={handleAttachClick}
          disabled={isUploading || isGenerating}
          className={`p-2.5 rounded-full transition flex items-center justify-center disabled:opacity-40 ${
            isNight 
              ? "text-slate-400 hover:text-indigo-400 hover:bg-slate-800" 
              : "text-slate-400 hover:text-indigo-600 hover:bg-slate-100"
          }`}
          title="Upload image or document"
        >
          {isUploading ? (
            <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 rotate-45" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          )}
        </button>

        {/* Voice button */}
        <button
          suppressHydrationWarning
          onClick={handleVoiceToggle}
          disabled={isGenerating}
          className={`p-2.5 rounded-full transition flex items-center justify-center disabled:opacity-40 ${
            isListening 
              ? "bg-red-500/20 text-red-500 animate-pulse" 
              : isNight 
                ? "text-slate-400 hover:text-indigo-400 hover:bg-slate-800" 
                : "text-slate-400 hover:text-indigo-600 hover:bg-slate-100"
          }`}
          title={isListening ? "Listening... click to stop" : "Voice input"}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </button>

        {/* Text Input */}
        <input
          suppressHydrationWarning
          type="text"
          placeholder={isGenerating ? "Saki is generating..." : isListening ? "Listening to your voice..." : "Message Saki..."}
          className={`flex-1 bg-transparent text-sm md:text-base focus:outline-none ml-1.5 ${
            isNight ? "text-white placeholder-slate-500" : "text-slate-800 placeholder-slate-400"
          }`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGenerating}
        />
        
        {/* Send / Stop Action Button */}
        {isGenerating ? (
          <button
            suppressHydrationWarning
            onClick={onStop}
            className="ml-2 px-3.5 py-2.5 rounded-full bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white transition-all transform hover:scale-105 active:scale-95 shadow-md flex items-center gap-1.5 font-bold text-xs"
            title="Stop generation"
          >
            <span className="w-2 h-2 bg-white rounded-2xs animate-pulse"></span>
            <span>Stop</span>
          </button>
        ) : (
          <button
            suppressHydrationWarning
            onClick={handleSend}
            disabled={(!input.trim() && attachments.length === 0) || isUploading}
            className="ml-2 p-2.5 rounded-full bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white transition-all transform hover:scale-105 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed shadow-md flex items-center justify-center"
            title="Send message"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
