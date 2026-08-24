export interface ChatAttachment {
  name: string;
  path: string;
  type?: string;
  size?: string;
}

export type SakiState = 
  | "IDLE"
  | "LISTENING"
  | "PROCESSING"
  | "THINKING"
  | "SEARCHING"
  | "VISION"
  | "REMEMBERING"
  | "ACTING"
  | "SPEAKING"
  | "ERROR";

export interface SakiEvent {
  event_id: string;
  event_type: "state_change" | "token" | "status" | "error" | "lifecycle";
  conversation_id: string;
  request_id: string;
  state: SakiState;
  previous_state?: SakiState | null;
  activity?: string | null;
  task?: string | null;
  selected_model?: string | null;
  detected_language?: string | null;
  memory_usage?: Record<string, unknown>;
  retrieval_status?: string | null;
  active_tool?: string | null;
  capability?: string | null;
  timestamp: number;
  latency_ms?: number | null;
  first_token_latency_ms?: number | null;
  details?: Record<string, unknown>;
  error?: string | null;
}

export interface SakiStateSnapshot {
  state: SakiState;
  conversation_id: string;
  selected_model?: string | null;
  activity?: string | null;
  task?: string | null;
  detected_language?: string | null;
  timestamp: number;
  history: SakiEvent[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: number;
  message_count: number;
  preview: string;
}

export interface GroupedConversations {
  active_id?: string;
  today: ConversationSummary[];
  yesterday: ConversationSummary[];
  last_7_days?: ConversationSummary[];
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
  cpu_percent?: number;
  loaded_models_count: number;
  active_components?: string[];
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
  reduced_animation?: boolean;
  personality_warmth?: number;
  personality_playfulness?: number;
  personality_verbosity?: number;
  privacy_mode?: string;
  auto_keep_alive?: string;
  core_quality?: "auto" | "low" | "medium" | "high" | "ultra";
  core_opacity?: number;
  core_show_hud?: boolean;
  audio_sensitivity?: number;
  voice_enabled?: boolean;
  voice_id?: string;
  voice_speed?: number;
  system_volume?: number;
  stt_model?: string;
  tts_voice?: string;
}

export interface VoiceStatusData {
  enabled: boolean;
  active_provider: string;
  default_voice: string;
  default_speed: number;
  kokoro_status: {
    initialized: boolean;
    available: boolean;
    device: string;
    model_size_mb: number;
    supported_female_voices: string[];
    error?: string | null;
  };
  piper_status: {
    available: boolean;
    supported_female_voices: string[];
  };
}

export interface ServerTimeData {
  datetime: string;
  time_12h: string;
  time_24h: string;
  date_display: string;
  date_short: string;
  day_of_week: string;
  time_of_day: string;
  time_emoji: string;
  is_weekend: boolean;
  day_type: string;
  greeting: string;
  human_description: string;
  timezone: string;
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

export interface VoiceTurnResponse {
  transcript: string;
  response_text: string;
  conversation_id: string;
  request_id: string;
  selected_model: string;
  task_type: string;
  conversation_mode: string;
  detected_language: string;
  language_confidence?: number;
  output_language?: string;
  language_profile?: Record<string, unknown>;
  has_audio: boolean;
  audio_base64?: string | null;
  audio_duration_sec: number;
  voice_used: string;
  tts_provider: string;
  latencies: {
    stt_latency_ms: number;
    llm_latency_ms: number;
    tts_latency_ms: number;
    total_latency_ms: number;
  };
  memory_count: number;
  interrupted: boolean;
  interrupted_at_sec?: number;
  success: boolean;
  error?: string | null;
}

export async function sendChatMessage(
  message: string,
  attachments: ChatAttachment[] = [],
  conversation_id: string = "default-session",
  signal?: AbortSignal,
  language_mode: string = "AUTO"
): Promise<{ response: string; routing?: Record<string, unknown>; error?: string } | null> {
  try {
    const res = await fetchWithFallback("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, attachments, conversation_id, language_mode }),
      signal
    });
    if (res.ok) {
      const data = await res.json();
      return {
        response: data.response || "",
        routing: data.routing
      };
    }
    const errText = await res.text();
    return { response: "", error: `Status ${res.status}: ${errText}` };
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") return null;
    return { response: "", error: String(err) };
  }
}

export async function streamChat(
  message: string,
  attachments: ChatAttachment[],
  onChunk: (text: string) => void,
  signal?: AbortSignal,
  conversation_id?: string,
  onStateChange?: (event: SakiEvent) => void,
  language_mode: string = "AUTO"
) {
  let tokenCount = 0;
  try {
    const res = await fetchWithFallback("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream, text/plain, */*"
      },
      body: JSON.stringify({ message, attachments, conversation_id, language_mode }),
      signal
    });

    if (!res.ok) {
      console.warn(`[streamChat] /api/chat/stream returned status ${res.status}, using REST fallback...`);
      const fallback = await sendChatMessage(message, attachments, conversation_id, signal, language_mode);
      if (fallback?.response) {
        onChunk(fallback.response);
      } else {
        onChunk(`⚠️ Backend error (${res.status}): ${fallback?.error || "Could not generate response."}`);
      }
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      const fallback = await sendChatMessage(message, attachments, conversation_id, signal);
      if (fallback?.response) {
        onChunk(fallback.response);
      } else {
        onChunk("⚠️ Error: ReadableStream not supported by browser or backend.");
      }
      return;
    }

    const decoder = new TextDecoder("utf-8");
    let done = false;
    let sseBuffer = "";

    while (!done) {
      if (signal?.aborted) {
        await reader.cancel();
        break;
      }

      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        const text = decoder.decode(value, { stream: true });
        sseBuffer += text;

        const lines = sseBuffer.split("\n");
        sseBuffer = lines.pop() || ""; // Keep incomplete line in buffer

        let currentEventType = "message";
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("event:")) {
            currentEventType = trimmed.slice(6).trim();
          } else if (trimmed.startsWith("data:")) {
            const dataStr = trimmed.slice(5).trim();
            if (!dataStr) continue;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.event_type === "state_change" || currentEventType === "state_change") {
                onStateChange?.(parsed as SakiEvent);
              } else if (parsed.event_type === "token" || currentEventType === "token") {
                const chunkText = parsed.details?.chunk ?? parsed.chunk ?? "";
                if (chunkText) {
                  tokenCount++;
                  onChunk(chunkText);
                }
              } else if (parsed.event_type === "error" || currentEventType === "error") {
                onStateChange?.(parsed as SakiEvent);
                if (parsed.error) {
                  onChunk(`\n⚠️ Error: ${parsed.error}\n`);
                }
              }
            } catch {
              // Non-JSON raw data
              tokenCount++;
              onChunk(dataStr);
            }
          } else if (trimmed && !trimmed.startsWith(":")) {
            // Raw text fallback
            tokenCount++;
            onChunk(line);
          }
        }
      }
    }

    // If stream completed with 0 tokens received, attempt non-streaming fallback
    if (tokenCount === 0 && !signal?.aborted) {
      console.warn("[streamChat] Stream closed with 0 tokens, falling back to non-streaming /api/chat");
      const fallback = await sendChatMessage(message, attachments, conversation_id, signal);
      if (fallback?.response) {
        onChunk(fallback.response);
      }
    }
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") {
      return;
    }
    console.warn("Streaming chat error, attempting REST fallback:", error);
    try {
      const fallback = await sendChatMessage(message, attachments, conversation_id, signal);
      if (fallback?.response) {
        onChunk(fallback.response);
        return;
      }
    } catch {}
    onChunk("⚠️ Connection Error: Unable to reach Saki Backend. Please ensure the server is started.");
  }
}

export function subscribeToStateStream(
  onEvent: (event: SakiEvent) => void,
  conversationId?: string
): () => void {
  const url = conversationId
    ? `http://127.0.0.1:8000/api/state/stream?conversation_id=${encodeURIComponent(conversationId)}`
    : `http://127.0.0.1:8000/api/state/stream`;

  let eventSource: EventSource | null = null;
  try {
    eventSource = new EventSource(url);
    eventSource.addEventListener("state_change", (e) => {
      try {
        const evt = JSON.parse(e.data);
        onEvent(evt);
      } catch (err) {
        console.error("Failed to parse state_change event:", err);
      }
    });
    eventSource.addEventListener("status", (e) => {
      try {
        const evt = JSON.parse(e.data);
        onEvent(evt);
      } catch (err) {
        console.error("Failed to parse status event:", err);
      }
    });
    eventSource.addEventListener("error", (e) => {
      try {
        const evt = JSON.parse((e as MessageEvent).data);
        onEvent(evt);
      } catch {
        // Ignore heartbeat/network reconnects
      }
    });
  } catch (err) {
    console.error("Failed to create EventSource:", err);
  }

  return () => {
    if (eventSource) {
      eventSource.close();
    }
  };
}

export async function getCurrentState(conversationId?: string): Promise<SakiStateSnapshot | null> {
  try {
    const path = conversationId 
      ? `/api/state/current?conversation_id=${encodeURIComponent(conversationId)}`
      : `/api/state/current`;
    const res = await fetchWithFallback(path);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.error("Error fetching current state:", err);
  }
  return null;
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

export async function getServerTime(): Promise<ServerTimeData | null> {
  try {
    const res = await fetchWithFallback("/api/time");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch server time:", err);
  }
  return null;
}



export async function fetchSpeechAudio(
  text: string,
  voice: string = "af_heart",
  speed: number = 1.0,
  signal?: AbortSignal
): Promise<Blob | null> {
  try {
    const res = await fetchWithFallback("/api/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice, speed }),
      signal
    });

    if (!res.ok) {
      console.warn(`TTS synthesis returned status ${res.status}`);
      return null;
    }

    return await res.blob();
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      return null;
    }
    console.error("Failed to fetch speech audio:", err);
    return null;
  }
}

export async function stopSpeech(): Promise<boolean> {
  try {
    const res = await fetchWithFallback("/api/voice/stop", {
      method: "POST"
    });
    return res.ok;
  } catch (err) {
    console.warn("Failed to cancel speech:", err);
    return false;
  }
}

export async function interruptVoice(conversationId: string = "voice-session"): Promise<boolean> {
  try {
    const res = await fetchWithFallback("/api/voice/interrupt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, reason: "user_barge_in" })
    });
    return res.ok;
  } catch (err) {
    console.warn("Failed to trigger voice interrupt:", err);
    return false;
  }
}

export async function executeVoiceTurn(
  audioBase64: string,
  conversationId: string = "voice-session",
  voice: string = "af_heart",
  speed: number = 1.0,
  signal?: AbortSignal
): Promise<VoiceTurnResponse | null> {
  try {
    const res = await fetchWithFallback("/api/voice/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_base64: audioBase64,
        conversation_id: conversationId,
        voice,
        speed,
        play_locally: false
      }),
      signal
    });

    if (res.ok) {
      return (await res.json()) as VoiceTurnResponse;
    }
    return null;
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") return null;
    console.warn("Failed to execute voice turn:", err);
    return null;
  }
}

export async function transcribeAudio(
  audioBase64: string,
  language?: string,
  signal?: AbortSignal
): Promise<{ transcript: string; language: string; latency_ms: number; success: boolean } | null> {
  try {
    const res = await fetchWithFallback("/api/voice/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_base64: audioBase64,
        language: language || null
      }),
      signal
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to transcribe audio:", err);
  }
  return null;
}

export async function startVoiceSession(
  conversationId: string = "voice-session",
  voice: string = "af_heart"
): Promise<boolean> {
  try {
    const res = await fetchWithFallback("/api/voice/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, voice })
    });
    return res.ok;
  } catch (err) {
    console.warn("Failed to start voice session:", err);
    return false;
  }
}

export async function stopVoiceSession(): Promise<boolean> {
  try {
    const res = await fetchWithFallback("/api/voice/session/stop", {
      method: "POST"
    });
    return res.ok;
  } catch (err) {
    console.warn("Failed to stop voice session:", err);
    return false;
  }
}

export async function getVoiceStatus(): Promise<VoiceStatusData | null> {
  try {
    const res = await fetchWithFallback("/api/voice/status");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to get voice status:", err);
  }
  return null;
}

export async function getVoiceList(): Promise<{ voices: string[]; recommended_voice: string } | null> {
  try {
    const res = await fetchWithFallback("/api/voice/voices");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch voices list:", err);
  }
  return null;
}

export async function getSystemResources(): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetchWithFallback("/api/system/resources");
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Failed to fetch system resources:", err);
  }
  return null;
}

export async function unloadResource(componentId: string, force: boolean = false): Promise<boolean> {
  try {
    const res = await fetchWithFallback("/api/system/resources/unload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ component_id: componentId, force })
    });
    if (res.ok) {
      const data = await res.json();
      return Boolean(data.success);
    }
  } catch (err) {
    console.warn("Failed to unload resource:", err);
  }
  return false;
}