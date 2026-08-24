import { useState } from "react";
import { ChatAttachment } from "../lib/api";
import { SakiTheme } from "../lib/theme";

interface MessageBubbleProps {
  role: string;
  text: string;
  attachments?: ChatAttachment[];
  theme?: SakiTheme;
  onRetry?: () => void;
}

export default function MessageBubble({ 
  role, 
  text, 
  attachments = [], 
  theme = "night_sky",
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
    if (!isUser) {
      cleaned = cleaned.replace(/^(?:saki|assistant|ai)\s*[-:：]\s*/i, "");
    }
    return cleaned;
  };

  const renderInlineFormatted = (rawText: string) => {
    const codeParts = rawText.split(/(`[^`\n]+`)/g);

    return codeParts.map((part, pIdx) => {
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code 
            key={`code-${pIdx}`} 
            className={`px-1.5 py-0.5 rounded font-mono text-xs mx-0.5 border ${
              isNight
                ? "bg-slate-900/90 text-cyan-300 border-cyan-500/30"
                : "bg-sky-100/90 text-sky-900 border-sky-300 font-semibold"
            }`}
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      const boldParts = part.split(/(\*\*.*?\*\*)/g);
      return boldParts.map((bPart, bIdx) => {
        if (bPart.startsWith("**") && bPart.endsWith("**")) {
          return (
            <strong 
              key={`bold-${pIdx}-${bIdx}`} 
              className={`font-extrabold ${
                isNight
                  ? isUser ? "text-white" : "text-cyan-100"
                  : isUser ? "text-sky-950" : "text-slate-950"
              }`}
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
        <ul key={keyPrefix} className="space-y-1.5 my-2 pl-1">
          {lines.filter((l) => l.trim().length > 0).map((line, lIdx) => {
            const content = line.trim().replace(/^[-*]\s+/, "");
            return (
              <li key={`${keyPrefix}-${lIdx}`} className="flex items-start gap-2">
                <span className={`inline-block w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 ${
                  isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-600 shadow-[0_0_4px_#0284c7]"
                }`} />
                <span className="flex-1 leading-relaxed">{renderInlineFormatted(content)}</span>
              </li>
            );
          })}
        </ul>
      );
    }

    if (isNumberedList && lines.some((l) => l.trim().length > 0)) {
      return (
        <ol key={keyPrefix} className="space-y-1.5 my-2 pl-1">
          {lines.filter((l) => l.trim().length > 0).map((line, lIdx) => {
            const match = line.trim().match(/^(\d+)\.\s+(.*)$/);
            const num = match ? match[1] : `${lIdx + 1}`;
            const content = match ? match[2] : line.trim();
            return (
              <li key={`${keyPrefix}-${lIdx}`} className="flex items-start gap-2">
                <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-md mt-0.5 flex-shrink-0 border ${
                  isNight
                    ? "bg-cyan-950/70 text-cyan-300 border-cyan-500/40"
                    : "bg-sky-100 text-sky-800 border-sky-300"
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
      <p key={keyPrefix} className="my-1.5 leading-relaxed">
        {renderInlineFormatted(block)}
      </p>
    );
  };

  const renderContent = (rawText: string) => {
    const cleaned = sanitizeContent(rawText);
    const codeBlockRegex = /```([a-zA-Z]*)\n([\s\S]*?)```/g;
    const parts: Array<{ type: "text" | "code"; content: string; lang?: string }> = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(cleaned)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: "text", content: cleaned.slice(lastIndex, match.index) });
      }
      parts.push({ type: "code", lang: match[1] || "code", content: match[2].trim() });
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < cleaned.length) {
      parts.push({ type: "text", content: cleaned.slice(lastIndex) });
    }

    return parts.map((part, index) => {
      if (part.type === "code") {
        const lang = part.lang || "code";
        const code = part.content;
        return (
          <div key={`code-block-${index}`} className="my-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/95 shadow-lg">
            <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-slate-800 text-xs">
              <span className="font-mono text-[10px] text-cyan-400 font-bold uppercase tracking-wider">{lang}</span>
              <button
                suppressHydrationWarning
                onClick={() => handleCopy(code, index)}
                className="text-[10px] font-mono text-slate-400 hover:text-cyan-300 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 transition cursor-pointer"
              >
                {copiedIndex === index ? "✓ COPIED" : "COPY"}
              </button>
            </div>
            <pre className="p-3.5 overflow-x-auto leading-relaxed text-[11px] text-cyan-100 font-mono">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      const paragraphs = part.content.split(/\n\s*\n+/);
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
      <div className={`flex flex-col gap-1.5 mt-2.5 pt-2 border-t ${isNight ? "border-cyan-500/15" : "border-sky-300/40"}`}>
        <span className="hud-label text-[9px] font-bold opacity-80">Attached Artifacts</span>
        <div className="flex flex-wrap gap-2">
          {attachments.map((att, i) => (
            <div 
              key={i} 
              className={`flex items-center gap-2 border text-xs px-2.5 py-1 rounded-lg font-mono shadow-sm ${
                isNight
                  ? "border-cyan-500/25 bg-slate-900/80 text-cyan-200"
                  : "border-sky-300 bg-white/90 text-sky-900"
              }`}
            >
              <span className="text-[10px]">📎</span>
              <span className={`text-[9px] font-bold px-1 rounded border ${
                isNight
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                  : "bg-sky-100 text-sky-800 border-sky-300"
              }`}>
                {att.type || "FILE"}
              </span>
              <span className="truncate max-w-[140px] text-[11px] font-medium">{att.name}</span>
              {att.size && <span className="text-[9px] opacity-70">({att.size})</span>}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className={`flex w-full mb-3 animate-slide-up ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`relative px-4 py-3 max-w-[90%] md:max-w-[80%] text-xs leading-relaxed hud-corner-bracket transition-all duration-300 ${
          isUser
            ? isNight
              ? "bg-slate-900/80 text-slate-100 rounded-2xl rounded-tr-xs border border-indigo-500/35 shadow-[0_4px_24px_rgba(99,102,241,0.15)] backdrop-blur-md"
              : "bg-sky-100/90 text-sky-950 rounded-2xl rounded-tr-xs border border-sky-300/80 shadow-[0_4px_20px_rgba(14,165,233,0.15)] backdrop-blur-md"
            : isNight
            ? "bg-slate-950/70 text-slate-100 rounded-2xl rounded-tl-xs border border-cyan-500/25 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-md"
            : "bg-white/90 text-slate-900 rounded-2xl rounded-tl-xs border border-sky-200/90 shadow-[0_8px_32px_rgba(14,165,233,0.12)] backdrop-blur-md"
        }`}
      >
        {/* Role & Telemetry Header */}
        <div className={`flex items-center justify-between pb-1.5 mb-1.5 border-b ${isNight ? "border-cyan-500/10" : "border-sky-200/50"}`}>
          <div className="flex items-center gap-1.5">
            <span className={`hud-label font-bold text-[9px] ${
              isUser
                ? isNight ? "text-indigo-400" : "text-indigo-700"
                : isNight ? "text-cyan-400" : "text-sky-700"
            }`}>
              {isUser ? "OPERATOR // USER" : "SAKI // CORE_AI"}
            </span>
            {!isUser && (
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${isNight ? "bg-cyan-400 shadow-[0_0_6px_#38bdf8]" : "bg-sky-500 shadow-[0_0_6px_#0284c7]"}`} />
            )}
          </div>
          <span className={`text-[8px] font-mono ${isNight ? "text-slate-500" : "text-slate-400"}`}>
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Message Content with High Contrast */}
        <div className={isNight ? "text-slate-200" : "text-slate-800 font-normal"}>
          {renderContent(text)}
        </div>

        {renderAttachments()}

        {!isUser && onRetry && (
          <div className={`mt-2 pt-1.5 border-t flex justify-end ${isNight ? "border-cyan-500/10" : "border-sky-200/40"}`}>
            <button
              onClick={onRetry}
              className={`text-[10px] font-mono font-semibold flex items-center gap-1 transition cursor-pointer ${
                isNight ? "text-slate-400 hover:text-cyan-300" : "text-slate-500 hover:text-sky-700"
              }`}
              title="Regenerate response"
              suppressHydrationWarning
            >
              <span>↻</span>
              <span>RETRY TURN</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
