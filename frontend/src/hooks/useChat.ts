"use client";

import { useState } from "react";
import { Message } from "@/lib/types";
import { streamChat } from "@/lib/api";
import { chatSchema } from "@/lib/validators";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function sendMessage(input: string) {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    };

    const botMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage, botMessage]);
    setLoading(true);

    try {
      await streamChat(trimmed, (chunk) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMessage.id
              ? { ...msg, content: msg.content + chunk }
              : msg
          )
        );
      });
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMessage.id
            ? { ...msg, content: "Error: " + err.message }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  }

  return { messages, sendMessage, loading };
}
