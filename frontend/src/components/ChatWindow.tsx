import { useState } from "react";
import MessageBubble from "./MessageBubble";
import InputBox from "./InputBox";
import { streamChat } from "../lib/api";

export default function ChatWindow() {
  const [messages, setMessages] = useState<any[]>([]);

  const sendMessage = async (text: string) => {
    const newMessages = [...messages, { role: "user", content: text }];
    setMessages(newMessages);

    let assistantText = "";

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    await streamChat(newMessages, (chunk) => {
      assistantText += chunk;

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].content = assistantText;
        return updated;
      });
    });
  };

  return (
    <div className="flex flex-col h-screen p-4 gap-4">
      <div className="flex-1 overflow-y-auto space-y-2">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} text={m.content} />
        ))}
      </div>
      <InputBox onSend={sendMessage} />
    </div>
  );
}
