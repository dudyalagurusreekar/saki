"use client";

import { Message } from "@/lib/types";

interface MessageBubbleProps {
  msg: Message;
}

export default function MessageBubble({ msg }: MessageBubbleProps) {
  const isUser = msg.role === "user";

  return (
    <div
      className={lex }
    >
      <div
        className={max-w-[80%] px-4 py-2 rounded-lg }
      >
        {msg.content || "…"}
      </div>
    </div>
  );
}
