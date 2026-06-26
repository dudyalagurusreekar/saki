"use client";

import { Message } from "@/lib/types";

interface MessageBubbleProps {
  msg: Message;
}

export default function MessageBubble({ msg }: MessageBubbleProps) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-4 py-2 rounded-lg ${
          isUser ? "bg-purple-600 text-white" : "bg-gray-100 text-gray-900"
        }`}
      >
        {msg.content || "\u2026"}
      </div>
    </div>
  );
}
