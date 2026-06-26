export async function streamChat(message: string, onChunk: (text: string) => void) {
  const res = await fetch("http://localhost:8000/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    onChunk("Error: " + res.statusText);
    return;
  }

  const data = await res.json();
  const text = data.response || "";

  // simulate word-by-word streaming for UX
  const words = text.split(" ");
  for (let i = 0; i < words.length; i++) {
    onChunk((i === 0 ? "" : " ") + words[i]);
    await new Promise((r) => setTimeout(r, 30));
  }
}