export interface ChatAttachment {
  name: string;
  path: string;
  type?: string;
  size?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: number;
  message_count: number;
  preview: string;
}

export interface GroupedConversations {
  active_id: string;
  today: ConversationSummary[];
  yesterday: ConversationSummary[];
  older: ConversationSummary[];
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  messages: Array<{
    role: string;
    content: string;
    attachments?: ChatAttachment[];
  }>;
}

export interface BrainStatusData {
  model: string;
  mode: string;
  state: string;
  latency_ms: number;
  first_token_latency: number;
  tokens_per_second: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  memory_count: number;
  rag_enabled: boolean;
  gpu_name: string;
  vram_usage: string;
  ram_usage: string;
  loaded_models_count: number;
  awareness?: {
    current_activity?: string;
    current_project?: string;
    conversation_mode?: string;
    emotional_state?: {
      emotion: string;
      intensity: number;
      confidence: number;
      cause: string;
      needs: string[];
    };
    social_energy?: {
      energy: number;
      warmth: number;
      playfulness: number;
      seriousness: number;
    };
    last_model?: string;
  };
  cognitive_state?: {
    conversation?: {
      topic: string;
      mode: string;
      task: string;
      stage: string;
    };
    uncertainty?: {
      routing_confidence: number;
      emotion_confidence: number;
      memory_relevance: number;
    };
  };
}

export interface SystemHealthData {
  status: "Online" | "Degraded" | "Offline";
  backend: string;
  ollama_connected: boolean;
  loaded_models: string[];
  available_models: string[];
  memory_system: string;
}

export interface AppSettings {
  theme: "clear_sky" | "night_sky";
  reduced_animation: boolean;
  personality_warmth: number;
  personality_playfulness: number;
  personality_verbosity: number;
  privacy_mode: string;
  auto_keep_alive: string;
}

const API_ENDPOINTS = [
  "", // Same-origin relative path (Proxied by Next.js)
  "http://127.0.0.1:8000",
  "http://localhost:8000"
];

async function fetchWithFallback(path: string, options?: RequestInit): Promise<Response> {
  let lastError: unknown = null;
  for (const base of API_ENDPOINTS) {
    try {
      const res = await fetch(`${base}${path}`, options);
      return res;
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        throw err;
      }
      lastError = err;
    }
  }
  throw lastError || new Error("Failed to connect to backend server");
}

export async function streamChat(
  message: string,
  attachments: ChatAttachment[],
  onChunk: (text: string) => void,
  signal?: AbortSignal,
  conversation_id?: string
) {
  try {
    const res = await fetchWithFallback("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, attachments, conversation_id }),
      signal
    });

    if (!res.ok) {
      onChunk(`⚠️ Backend returned status error (${res.status}). Please check server logs.`);
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      onChunk("⚠️ Error: ReadableStream not supported by browser or backend.");
      return;
    }

    const decoder = new TextDecoder("utf-8");
    let done = false;

    while (!done) {
      if (signal?.aborted) {
        await reader.cancel();
        break;
      }

      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        onChunk(chunk);
      }
    }
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") {
      return;
    }
    console.error("Error streaming chat:", error);
    onChunk("⚠️ Connection Error: Unable to reach Saki Backend. Please ensure the server is started using `run_saki.bat` or `python start_saki.py`.");
  }
}

export async function getHealth(): Promise<SystemHealthData | null> {
  try {
    const res = await fetchWithFallback("/api/health");
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Return offline state if request fails
    return {
      status: "Offline",
      backend: "error",
      ollama_connected: false,
      loaded_models: [],
      available_models: [],
      memory_system: "unknown"
    };
  }
  return null;
}

export async function getBrainStatus(): Promise<BrainStatusData | null> {
  try {
    const res = await fetchWithFallback("/api/brain/status");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch brain status:", err);
  }
  return null;
}

export async function getConfig() {
  try {
    const res = await fetchWithFallback("/api/config");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend /config endpoint not available yet:", err);
  }
  return null;
}

export async function getMemory() {
  try {
    const res = await fetchWithFallback("/api/memory");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend /memory endpoint not available yet:", err);
  }
  return null;
}

export async function getSettings(): Promise<AppSettings | null> {
  try {
    const res = await fetchWithFallback("/api/settings");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Backend /settings endpoint not available yet:", err);
  }
  return null;
}

export async function saveSettings(settings: Partial<AppSettings>): Promise<AppSettings | null> {
  try {
    const res = await fetchWithFallback("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error("Failed to save settings:", err);
  }
  return null;
}

export async function getConversations(): Promise<GroupedConversations | null> {
  try {
    const res = await fetchWithFallback("/api/conversations");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch conversations:", err);
  }
  return null;
}

export async function searchConversations(query: string) {
  try {
    const res = await fetchWithFallback(`/api/conversations/search?q=${encodeURIComponent(query)}`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to search conversations:", err);
  }
  return { query, results: [] };
}

export async function getConversation(id: string): Promise<ConversationDetail | null> {
  try {
    const res = await fetchWithFallback(`/api/conversations/${encodeURIComponent(id)}`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`Failed to fetch conversation ${id}:`, err);
  }
  return null;
}

export async function createConversation(): Promise<ConversationDetail | null> {
  try {
    const res = await fetchWithFallback("/api/conversations/new", {
      method: "POST"
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error("Failed to create conversation:", err);
  }
  return null;
}

export async function deleteConversation(id: string): Promise<boolean> {
  try {
    const res = await fetchWithFallback(`/api/conversations/${encodeURIComponent(id)}`, {
      method: "DELETE"
    });
    return res.ok;
  } catch (err) {
    console.error(`Failed to delete conversation ${id}:`, err);
    return false;
  }
}

export async function uploadFile(file: File): Promise<ChatAttachment> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetchWithFallback("/api/upload", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Failed to upload file to server (" + res.status + ")");
  }

  return res.json();
}