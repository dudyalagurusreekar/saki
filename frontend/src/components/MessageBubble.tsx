import { useState } from "react";
import { ChatAttachment } from "../lib/api";

interface MessageBubbleProps {
  role: string;
  text: string;
  attachments?: ChatAttachment[];
  theme?: "clear_sky" | "night_sky";
  onRetry?: () => void;
}

export default function MessageBubble({ 
  role, 
  text, 
  attachments = [], 
  theme = "clear_sky",
  onRetry 
}: MessageBubbleProps) {
  const isUser = role === "user";
  const isNight = theme === "night_sky";
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const sanitizeContent = (raw: string) => {
    if (!raw) return "";
    let cleaned = raw;
    // Strip leading speaker tags if any leaked
    if (!isUser) {
      cleaned = cleaned.replace(/^(?:saki|assistant|ai)\s*[-:：]\s*/i, "");
    }
    return cleaned;
  };

  const renderInlineFormatted = (rawText: string) => {
    // Split by inline code `...`
    const codeParts = rawText.split(/(`[^`\n]+`)/g);

    return codeParts.map((part, pIdx) => {
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code 
            key={`code-${pIdx}`} 
            className={`px-1.5 py-0.5 rounded font-mono text-xs mx-0.5 border ${
              isNight 
                ? "bg-slate-800 text-indigo-300 border-slate-700" 
                : "bg-indigo-50 text-indigo-700 border-indigo-100"
            }`}
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      // Handle bold **text**
      const boldParts = part.split(/(\*\*.*?\*\*)/g);
      return boldParts.map((bPart, bIdx) => {
        if (bPart.startsWith("**") && bPart.endsWith("**")) {
          return (
            <strong 
              key={`bold-${pIdx}-${bIdx}`} 
              className={`font-black ${isUser ? "text-white" : isNight ? "text-white" : "text-slate-950"}`}
            >
              {bPart.slice(2, -2)}
            </strong>
          );
        }
        return bPart;
      });
    });
  };

  const renderParagraphOrBlock = (block: string, keyPrefix: string) => {
    const lines = block.split("\n");
    const isBulletList = lines.every((line) => line.trim().startsWith("- ") || line.trim().startsWith("* ") || line.trim() === "");
    const isNumberedList = lines.every((line) => /^\d+\.\s+/.test(line.trim()) || line.trim() === "");

    if (isBulletList && lines.some((l) => l.trim().length > 0)) {
      return (
        <ul key={keyPrefix} className="space-y-1.5 my-2.5 pl-1">
          {lines.filter((l) => l.trim().length > 0).map((line, lIdx) => {
            const content = line.trim().replace(/^[-*]\s+/, "");
            return (
              <li key={`${keyPrefix}-${lIdx}`} className="flex items-start gap-2">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0"></span>
                <span className="flex-1 leading-relaxed">{renderInlineFormatted(content)}</span>
              </li>
            );
          })}
        </ul>
      );
    }

    if (isNumberedList && lines.some((l) => l.trim().length > 0)) {
      return (
        <ol key={keyPrefix} className="space-y-1.5 my-2.5 pl-1">
          {lines.filter((l) => l.trim().length > 0).map((line, lIdx) => {
            const match = line.trim().match(/^(\d+)\.\s+(.*)$/);
            const num = match ? match[1] : `${lIdx + 1}`;
            const content = match ? match[2] : line.trim();
            return (
              <li key={`${keyPrefix}-${lIdx}`} className="flex items-start gap-2">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full mt-0.5 flex-shrink-0 ${
                  isNight ? "bg-indigo-950/80 text-indigo-300 border border-indigo-800" : "bg-indigo-100 text-indigo-700"
                }`}>
                  {num}
                </span>
                <span className="flex-1 leading-relaxed">{renderInlineFormatted(content)}</span>
              </li>
            );
          })}
        </ol>
      );
    }

    return (
      <div key={keyPrefix} className="mb-2.5 last:mb-0 leading-relaxed">
        {lines.map((l, lIdx) => (
          <div key={`${keyPrefix}-line-${lIdx}`}>
            {renderInlineFormatted(l)}
          </div>
        ))}
      </div>
    );
  };

  const renderContent = (content: string) => {
    if (!content) return null;
    const sanitized = sanitizeContent(content);

    // Split text by code blocks ```...```
    const parts = sanitized.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith("```") && part.endsWith("```")) {
        const rawCode = part.slice(3, -3).trim();
        const lines = rawCode.split("\n");
        const firstLine = lines[0].trim();
        const hasLang = /^[a-zA-Z0-9_#+-]+$/.test(firstLine);
        const lang = hasLang ? firstLine : "";
        const code = hasLang ? lines.slice(1).join("\n") : rawCode;

        return (
          <div 
            key={`code-block-${index}`} 
            className="my-3 rounded-2xl overflow-hidden border border-slate-800 bg-[#0f172a] shadow-lg text-slate-100 font-mono text-xs"
          >
            <div className="flex justify-between items-center px-4 py-2 bg-slate-900/90 border-b border-slate-800 select-none">
              <span className="text-[10px] uppercase font-bold text-indigo-400">
                {lang || "Code"}
              </span>
              <button
                onClick={() => handleCopy(code, index)}
                className="text-[10px] font-semibold text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition cursor-pointer"
              >
                {copiedIndex === index ? "✓ Copied!" : "Copy code"}
              </button>
            </div>
            <pre className="p-4 overflow-x-auto leading-relaxed">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      // Process normal text paragraphs
      const paragraphs = part.split(/\n\s*\n+/);
      return (
        <div key={`part-${index}`}>
          {paragraphs.map((p, pIdx) => renderParagraphOrBlock(p, `p-${index}-${pIdx}`))}
        </div>
      );
    });
  };

  const renderAttachments = () => {
    if (!attachments || attachments.length === 0) return null;

    return (
      <div className="flex flex-col gap-1.5 mt-2.5 pt-2 border-t border-slate-200/50 dark:border-slate-700/50">
        <span className="text-[10px] font-bold opacity-60 uppercase tracking-wide">Attached Files</span>
        <div className="flex flex-wrap gap-2">
          {attachments.map((att, i) => (
            <div 
              key={i} 
              className={`flex items-center gap-2 border text-xs px-3 py-1.5 rounded-xl font-medium shadow-2xs transition-all ${
                isUser 
                  ? "bg-indigo-700/90 border-indigo-500 text-white" 
                  : isNight 
                    ? "bg-slate-800/90 border-slate-700 text-slate-200" 
                    : "bg-white/90 border-slate-200 text-slate-700"
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <span className="font-bold bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 text-[9px] px-1.5 py-0.5 rounded-full">{att.type || "FILE"}</span>
              <span className="truncate max-w-[140px] font-semibold">{att.name}</span>
              {att.size && <span className="text-[10px] opacity-70">({att.size})</span>}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div
      className={`flex w-full mb-3.5 animate-slide-up ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && (
        <div className="flex-shrink-0 mr-2.5 mt-0.5">
          <div className="h-8 w-8 rounded-full overflow-hidden border-2 border-indigo-400/50 bg-white flex items-center justify-center shadow-xs">
            <img src="/saki.webp" alt="Saki DP" className="h-full w-full object-cover scale-105" />
          </div>
        </div>
      )}
      
      <div
        className={`relative px-4 py-3 max-w-[88%] md:max-w-[78%] text-sm leading-relaxed ${
          isUser
            ? "bg-gradient-to-br from-indigo-600 to-violet-600 text-white rounded-3xl rounded-br-xs shadow-md border border-indigo-500/30"
            : isNight
              ? "bg-[#1c2541]/90 text-slate-100 rounded-3xl rounded-bl-xs shadow-md border border-slate-700/80 backdrop-blur-md"
              : "bg-white/90 text-slate-800 rounded-3xl rounded-bl-xs shadow-xs border border-slate-200/80 backdrop-blur-md"
        }`}
      >
        <div className={isUser ? "text-white" : isNight ? "text-slate-100" : "text-slate-800"}>
          {renderContent(text)}
        </div>
        {renderAttachments()}

        {!isUser && onRetry && (
          <div className="mt-2 pt-1.5 border-t border-slate-200/40 dark:border-slate-700/40 flex justify-end">
            <button
              onClick={onRetry}
              className="text-[10px] font-semibold text-slate-400 hover:text-indigo-500 flex items-center gap-1 transition cursor-pointer"
              title="Regenerate response"
              suppressHydrationWarning
            >
              <span>↻</span>
              <span>Retry</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
