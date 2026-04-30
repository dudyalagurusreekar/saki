export async function streamChat(messages: any[], onChunk: (text: string) => void) {
  const res = await fetch("http://localhost:8000/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ messages }),
  });

  const reader = res.body?.getReader();
  const decoder = new TextDecoder("utf-8");

  if (!reader) return;

  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const json = line.replace("data: ", "");
        try {
          const parsed = JSON.parse(json);
          const content = parsed.message?.content || "";
          onChunk(content);
        } catch {}
      }
    }
  }
}