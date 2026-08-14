import { ChatAttachment } from "../lib/api";

interface MessageBubbleProps {
  role: string;
  text: string;
  attachments?: ChatAttachment[];
  uiMode?: "saki" | "chatgpt";
}

export default function MessageBubble({ role, text, attachments = [], uiMode = "saki" }: MessageBubbleProps) {
  const isUser = role === "user";

  const renderContent = (content: string) => {
    if (!content) return null;

    // Split text by code blocks ```
    const parts = content.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith("```") && part.endsWith("```")) {
        const rawCode = part.slice(3, -3).trim();
        const lines = rawCode.split("\n");
        const firstLine = lines[0].trim();
        const hasLang = /^[a-zA-Z0-9_#+-]+$/.test(firstLine);
        const lang = hasLang ? firstLine : "";
        const code = hasLang ? lines.slice(1).join("\n") : rawCode;

        return (
          <pre 
            key={index} 
            className="bg-slate-950 text-slate-100 p-4 rounded-xl text-xs md:text-sm my-3 overflow-x-auto font-mono shadow-inner border border-slate-800/80"
          >
            {lang && (
              <div className="flex justify-between items-center text-[10px] uppercase font-bold text-indigo-400 mb-2 border-b border-slate-800 pb-1.5 select-none">
                <span>{lang}</span>
                <span className="text-slate-500 font-normal">Code Block</span>
              </div>
            )}
            <code>{code}</code>
          </pre>
        );
      }

      // Handle inline code `code` and bold **text**
      const inlineParts = part.split(/(`[^`\n]+`)/g);

      return inlineParts.map((subPart, subIndex) => {
        if (subPart.startsWith("`") && subPart.endsWith("`")) {
          return (
            <code 
              key={`${index}-${subIndex}`} 
              className="bg-slate-100 text-pink-600 px-1.5 py-0.5 rounded font-mono text-xs md:text-sm mx-0.5 border border-slate-200"
            >
              {subPart.slice(1, -1)}
            </code>
          );
        }

        // Parse bold **text**
        const boldParts = subPart.split(/(\*\*.*?\*\*)/g);
        return boldParts.map((boldPart, boldIndex) => {
          if (boldPart.startsWith("**") && boldPart.endsWith("**")) {
            return (
              <strong 
                key={`${index}-${subIndex}-${boldIndex}`} 
                className="font-extrabold text-slate-900"
              >
                {boldPart.slice(2, -2)}
              </strong>
            );
          }
          return boldPart;
        });
      });
    });
  };

  const renderAttachments = () => {
    if (!attachments || attachments.length === 0) return null;

    return (
      <div className="flex flex-col gap-1.5 mt-3 pt-2.5 border-t border-slate-100/50">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Attached Files</span>
        <div className="flex flex-wrap gap-2">
          {attachments.map((att, i) => (
            <div 
              key={i} 
              className={`flex items-center gap-2 border text-xs px-3 py-1.5 rounded-xl font-medium shadow-sm transition-all ${
                isUser 
                  ? "bg-violet-850 border-violet-700 text-violet-100 hover:bg-violet-800" 
                  : "bg-white/80 border-slate-200/60 text-slate-700 hover:bg-white"
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <span className="font-semibold bg-indigo-500/20 text-indigo-700 text-[9px] px-1.5 py-0.5 rounded-full">{att.type || "FILE"}</span>
              <span className="truncate max-w-[150px]">{att.name}</span>
              {att.size && <span className="text-[10px] opacity-60">({att.size})</span>}
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (uiMode === "chatgpt") {
    return (
      <div className={`w-full py-6 px-4 md:px-0 ${isUser ? "bg-white" : "bg-[#f7f7f8] border-y border-black/5"}`}>
        <div className="max-w-3xl mx-auto flex gap-4 md:gap-6 text-base">
          <div className="flex-shrink-0">
            {isUser ? (
              <div className="h-[30px] w-[30px] rounded-sm bg-purple-600 text-white flex items-center justify-center font-bold text-sm shadow-sm select-none">
                U
              </div>
            ) : (
              <div className="h-[30px] w-[30px] rounded-sm bg-[#10a37f] p-0.5 overflow-hidden flex items-center justify-center shadow-sm">
                <img src="/logo.png" alt="ChatGPT" className="h-full w-full object-contain bg-white rounded-sm" />
              </div>
            )}
          </div>
          <div className="flex-1 text-gray-800 leading-[1.7] whitespace-pre-wrap">
            <div className="text-gray-800">{renderContent(text)}</div>
            {renderAttachments()}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex w-full mb-4 animate-slide-up px-4 md:px-0 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && (
        <div className="flex-shrink-0 mr-3">
          <div className="h-9 w-9 rounded-full overflow-hidden border border-[rgba(6,182,212,0.4)] status-indicator bg-white flex items-center justify-center shadow-[0_2px_8px_rgba(6,182,212,0.15)]">
            <img src="/logo.png" alt="Saki" className="h-full w-full object-contain" />
          </div>
        </div>
      )}
      
      <div
        className={`relative px-5 py-3.5 max-w-[85%] md:max-w-[70%] text-sm md:text-base leading-relaxed ${
          isUser
            ? "bg-[rgba(99,102,241,0.85)] text-white rounded-2xl rounded-br-sm shadow-[0_4px_20px_rgba(99,102,241,0.25)] border border-indigo-500/20"
            : "glass-panel text-slate-800 rounded-2xl rounded-bl-sm shadow-[0_4px_15px_rgba(0,0,0,0.03)] border border-slate-200/50"
        }`}
      >
        <div className={isUser ? "text-white" : "text-slate-800"}>
          {renderContent(text)}
        </div>
        {renderAttachments()}
      </div>
    </div>
  );
}
