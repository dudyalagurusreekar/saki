import { Message } from "@/lib/types";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div className="flex flex-col gap-2 p-4 overflow-y-auto h-[500px]">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} msg={msg} />
      ))}
    </div>
  );
}