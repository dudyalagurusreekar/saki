import { useState } from "react";

export default function InputBox({ onSend }: any) {
  const [input, setInput] = useState("");

  return (
    <div className="flex gap-2">
      <input
        className="flex-1 p-2 rounded bg-gray-800"
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button
        onClick={() => {
          onSend(input);
          setInput("");
        }}
        className="bg-green-500 px-4 rounded"
      >
        Send
      </button>
    </div>
  );
}
