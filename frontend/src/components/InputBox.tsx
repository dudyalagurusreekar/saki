import { useState, KeyboardEvent } from "react";

export default function InputBox({ onSend, uiMode = "saki" }: { onSend: (text: string) => void; uiMode?: "saki" | "chatgpt" }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSend();
    }
  };

  if (uiMode === "chatgpt") {
    return (
      <div className="w-full max-w-3xl mx-auto px-4 relative">
        <div className="relative flex items-center bg-white border border-gray-300 rounded-xl shadow-[0_0_15px_rgba(0,0,0,0.05)] p-1 pl-4">
          <input
            type="text"
            placeholder="Send a message..."
            className="flex-1 bg-transparent text-gray-800 placeholder-gray-500 text-base focus:outline-none min-h-[44px]"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
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
      <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-violet-400 to-cyan-300 opacity-20 blur-md group-hover:opacity-40 transition duration-500"></div>
      <div className="relative flex items-center bg-white/80 rounded-full border border-slate-200 shadow-xl p-2 pl-6 backdrop-blur-md">
        <input
          type="text"
          placeholder="Message Saki..."
          className="flex-1 bg-transparent text-slate-800 placeholder-slate-400 text-base md:text-lg focus:outline-none"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="ml-3 p-3 rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white transition-all transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_4px_15px_rgba(109,40,217,0.3)] flex items-center justify-center"
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
