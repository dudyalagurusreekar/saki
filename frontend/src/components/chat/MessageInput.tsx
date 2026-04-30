"use client";

import { useState } from "react";

export default function MessageInput({
  onSend,
  loading,
}: {
  onSend: (msg: string) => void;
  loading: boolean;
}) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput("");
  };

  return (
    <div className="flex gap-2 p-3 border-t">
      <input
        className="flex-1 border rounded-lg p-2 outline-none"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        placeholder="Type message..."
      />

      <button
        onClick={handleSend}
        disabled={loading}
        className="bg-black text-white px-4 rounded-lg disabled:opacity-50"
      >
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
}