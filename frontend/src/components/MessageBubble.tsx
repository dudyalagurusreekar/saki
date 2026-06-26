export default function MessageBubble({ role, text, uiMode = "saki" }: { role: string; text: string; uiMode?: "saki" | "chatgpt" }) {
  const isUser = role === "user";

  if (uiMode === "chatgpt") {
    return (
      <div className={`w-full py-6 px-4 md:px-0 ${isUser ? "bg-white" : "bg-[#f7f7f8] border-y border-black/5"}`}>
        <div className="max-w-3xl mx-auto flex gap-4 md:gap-6 text-base">
          <div className="flex-shrink-0">
            {isUser ? (
              <div className="h-[30px] w-[30px] rounded-sm bg-purple-600 text-white flex items-center justify-center font-bold text-sm">
                U
              </div>
            ) : (
              <div className="h-[30px] w-[30px] rounded-sm bg-[#10a37f] p-0.5 overflow-hidden flex items-center justify-center">
                <img src="/logo.png" alt="ChatGPT" className="h-full w-full object-contain bg-white rounded-sm" />
              </div>
            )}
          </div>
          <div className="flex-1 text-gray-800 leading-[1.7] whitespace-pre-wrap">
            {text}
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
          <div className="h-8 w-8 rounded-full overflow-hidden border border-[rgba(6,182,212,0.5)] status-indicator bg-white">
            <img src="/logo.png" alt="Saki" className="h-full w-full object-contain" />
          </div>
        </div>
      )}
      
      <div
        className={`relative px-5 py-3.5 max-w-[80%] md:max-w-[70%] text-sm md:text-base leading-relaxed ${
          isUser
            ? "bg-[rgba(109,40,217,0.8)] text-white rounded-2xl rounded-br-sm shadow-[0_4px_20px_rgba(109,40,217,0.3)]"
            : "glass-panel text-slate-800 rounded-2xl rounded-bl-sm shadow-[0_4px_15px_rgba(0,0,0,0.05)]"
        }`}
      >
        {/* Subtle text gradient for AI messages */}
        {text}
      </div>
    </div>
  );
}
