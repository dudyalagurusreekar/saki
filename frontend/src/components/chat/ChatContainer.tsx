"use client";

import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";

export default function ChatContainer() {
  const { messages, sendMessage, loading } = useChat();
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="max-w-2xl mx-auto border rounded-xl shadow-md flex flex-col">
      <MessageList messages={messages} />

      {loading && (
        <div className="px-4 text-sm text-gray-500">
          Saki is typing...
        </div>
      )}

      <div ref={bottomRef} />

      <MessageInput onSend={sendMessage} loading={loading} />
    </div>
  );
}