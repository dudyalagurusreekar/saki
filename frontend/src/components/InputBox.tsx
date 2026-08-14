import { useState, useRef, KeyboardEvent } from "react";
import { uploadFile, ChatAttachment } from "../lib/api";

interface InputBoxProps {
  onSend: (text: string, attachments: ChatAttachment[]) => void;
  uiMode?: "saki" | "chatgpt";
}

export default function InputBox({ onSend, uiMode = "saki" }: InputBoxProps) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (input.trim() || attachments.length > 0) {
      onSend(input.trim(), attachments);
      setInput("");
      setAttachments([]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
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
      
      // Approximate extension
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
      // Reset input value
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  if (uiMode === "chatgpt") {
    return (
      <div className="w-full max-w-3xl mx-auto px-4 relative">
        {/* Attachments list */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2 max-w-3xl mx-auto">
            {attachments.map((att, i) => (
              <div key={i} className="flex items-center gap-2 bg-gray-100 border border-gray-200 text-xs text-gray-700 px-3 py-1.5 rounded-lg font-medium shadow-sm">
                <span className="bg-gray-200 text-gray-800 text-[10px] px-1.5 py-0.5 rounded font-bold">{att.type}</span>
                <span className="truncate max-w-[150px]">{att.name}</span>
                <span className="text-[10px] text-gray-400">({att.size})</span>
                <button onClick={() => removeAttachment(i)} className="text-gray-400 hover:text-red-500 font-bold ml-1 transition">×</button>
              </div>
            ))}
          </div>
        )}

        <div className="relative flex items-center bg-white border border-gray-300 rounded-xl shadow-[0_0_15px_rgba(0,0,0,0.05)] p-1 pl-4">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={handleAttachClick}
            disabled={isUploading}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
            title="Attach file"
          >
            {isUploading ? (
              <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 rotate-45" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            )}
          </button>
          
          <input
            type="text"
            placeholder="Send a message..."
            className="flex-1 bg-transparent text-gray-800 placeholder-gray-500 text-base focus:outline-none min-h-[44px] ml-2"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          
          <button
            onClick={handleSend}
            disabled={(!input.trim() && attachments.length === 0) || isUploading}
            className="ml-2 p-1.5 rounded-lg bg-black text-white disabled:bg-gray-200 disabled:text-gray-400 transition-colors flex items-center justify-center mr-1"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>
        </div>
        <div className="text-center text-xs text-gray-500 mt-2 mb-2">
          ChatGPT can make mistakes. Consider verifying important information.
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full max-w-4xl mx-auto mt-2">
      {/* Attachments list */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3 px-4">
          {attachments.map((att, i) => (
            <div key={i} className="flex items-center gap-2 bg-white/70 border border-slate-200 text-xs text-slate-700 px-3 py-1.5 rounded-full font-medium shadow-md backdrop-blur-sm animate-slide-up">
              <span className="bg-indigo-100 text-indigo-700 text-[9px] px-2 py-0.5 rounded-full font-bold">{att.type}</span>
              <span className="truncate max-w-[150px] font-semibold">{att.name}</span>
              <span className="text-[10px] text-slate-400">({att.size})</span>
              <button onClick={() => removeAttachment(i)} className="text-slate-400 hover:text-red-500 font-bold ml-1 transition">×</button>
            </div>
          ))}
        </div>
      )}

      <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-violet-400 to-cyan-300 opacity-20 blur-md group-hover:opacity-40 transition duration-500"></div>
      <div className="relative flex items-center bg-white/80 rounded-full border border-slate-200 shadow-xl p-2 pl-4 backdrop-blur-md">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          onClick={handleAttachClick}
          disabled={isUploading}
          className="p-3 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-full transition flex items-center justify-center"
          title="Upload file"
        >
          {isUploading ? (
            <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 rotate-45" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          )}
        </button>

        <input
          type="text"
          placeholder="Message Saki..."
          className="flex-1 bg-transparent text-slate-800 placeholder-slate-400 text-base md:text-lg focus:outline-none ml-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        
        <button
          onClick={handleSend}
          disabled={(!input.trim() && attachments.length === 0) || isUploading}
          className="ml-3 p-3.5 rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white transition-all transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_4px_15px_rgba(109,40,217,0.3)] flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
