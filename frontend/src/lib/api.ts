export interface ChatAttachment {
  name: string;
  path: string;
  type?: string;
  size?: string;
}

export async function streamChat(
  message: string,
  attachments: ChatAttachment[],
  onChunk: (text: string) => void
) {
  try {
    const res = await fetch("http://localhost:8000/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, attachments }),
    });

    if (!res.ok) {
      onChunk("Error: Failed to fetch stream from backend (" + res.status + ")");
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      onChunk("Error: ReadableStream not supported by browser or backend.");
      return;
    }

    const decoder = new TextDecoder("utf-8");
    let done = false;

    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        onChunk(chunk);
      }
    }
  } catch (error: unknown) {
    console.error("Error streaming chat:", error);
    const msg = error instanceof Error ? error.message : String(error);
    onChunk("Error calling server: " + msg);
  }
}

export async function getConfig() {
  const res = await fetch("http://localhost:8000/api/config");
  if (!res.ok) {
    throw new Error("Failed to fetch backend configuration");
  }
  return res.json();
}

export async function getMemory() {
  const res = await fetch("http://localhost:8000/api/memory");
  if (!res.ok) {
    throw new Error("Failed to fetch conversation memory");
  }
  return res.json();
}

export async function uploadFile(file: File): Promise<ChatAttachment> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("http://localhost:8000/api/upload", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Failed to upload file to server");
  }

  return res.json();
}