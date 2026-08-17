# Saki AI — World Access Baseline & Architecture Discovery Document
**Sprint 0 Baseline Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Date**: August 17, 2026  
**Status**: Completed Architectural Baseline  

---

## 1. CURRENT ARCHITECTURE

The Saki AI system is an emotionally intelligent, local multi-model AI companion built as a decoupled full-stack architecture:

```
[ Frontend: Next.js 15 (App Router / TypeScript / Tailwind CSS) ]
                        │
                  (HTTP / JSON)
                        ▼
[ Backend: FastAPI (Python 3.12 / Pydantic v2 / Uvicorn) ]
    ├── Routes: chat, memory, system
    ├── Orchestration: SakiModelOrchestrator, ResponsePlanner, ResponseEvaluator
    ├── Cognition & Emotion: SakiAwareness, SakiCognitiveState, LearningService
    ├── Model Layer: ModelManager state machine -> Ollama HTTP API (:11434)
    ├── Memory Engine: JSON-backed durable store & conversation threads
    └── Privacy & Search: PrivacyGate (make_safe_query) -> SearchService -> Gemini/Placeholder
```

### Core Architecture Layers:
1. **Frontend Presentation**: Responsive 3-region layout (`Sidebar.tsx`, central `ChatWindow.tsx`, developer `BrainPanel.tsx`, `MemoryModal.tsx`, `SettingsModal.tsx`, `SkyBackground.tsx`).
2. **API Proxy Layer**: `next.config.ts` rewrites `/api/*` requests to `http://127.0.0.1:8000/api/*`.
3. **Backend Service Engine**: FastAPI application (`backend/main.py`) delegating to route modules (`backend/routes/`).
4. **Cognitive & Emotional Subsystem**:
   - `SakiModelOrchestrator` (`backend/services/orchestrator.py`): Routes user requests to optimal local LLM.
   - `SakiAwareness` (`backend/services/emotional_intelligence.py`): Analyzes user emotions, intensity, needs, social energy, active projects.
   - `SakiCognitiveState` (`backend/core/saki_state.py`): Models conversation topic, mode, task, stage, and uncertainty.
   - `ResponsePlanner` (`backend/services/response_planner.py`): Generates response blueprint before LLM invocation.
   - `ResponseEvaluator` (`backend/services/response_evaluator.py`): Sanitizes outputs, strips internal leaks, removes robotic cliches.
5. **Model Orchestration & Telemetry**:
   - `ModelManager` (`backend/services/model_manager.py`): State machine tracking `OFF`, `LOADING`, `ACTIVE`, `IDLE`, `UNLOADING`, `ERROR` states and recording latency, tok/s, first-token time, and token counts.
   - `ai_service.py` (`backend/services/ai_service.py`): HTTP client connecting to local Ollama endpoints (`http://localhost:11434/api/generate`).
6. **Data & Memory Storage**:
   - `data/memory.json`: Primary durable memory, categorized memories (`PREFERENCE`, `FACT`, `PROJECT`, `PATTERN`, `PROGRESS`, `DECISION`), user model, awareness, cognitive state.
   - `data/conversations.json`: Threaded conversation messages, timestamps, titles.
   - `data/settings.json`: Persisted user options (theme, privacy mode, personality parameters).

---

## 2. CURRENT CHAT FLOW

```
User Input (Frontend)
   │
   ▼
api.ts (streamChat / POST /api/chat/stream)
   │
   ▼
backend.routes.chat.chat_stream(req: ChatRequest)
   ├── 1. get_attachment_context(req) -> parses uploaded documents/images
   ├── 2. load_memory() -> fetches data/memory.json
   ├── 3. detect_user_correction(user_input) -> captures routing/style overrides
   ├── 4. SakiModelOrchestrator.classify_request() -> outputs RoutingDecision
   │        ├── analyze_emotional_state() -> detects emotion & needs
   │        ├── calculate_social_energy() -> modulates warmth/playfulness/seriousness
   │        └── selects specialist model (phi3 / hermes / qwen3 / coder / gemma)
   ├── 5. plan_response() -> generates ResponsePlan blueprint
   ├── 6. build_smart_memory_context() -> retrieves relevant durable memories
   ├── 7. build_saki_system_prompt() -> constructs system prompt with persona rules
   ├── 8. stream_model() -> streams tokens from Ollama with real-time telemetry
   ├── 9. is_helpless_response() -> if output is helpless ("I don't know"), triggers safe_search()
   ├── 10. evaluate_response() -> strips speaker prefixes, sanitizes internal leaks & cliches
   ├── 11. update_memory() -> persists user/saki interaction, awareness, durable facts
   └── 12. append_message_to_conversation() -> writes to data/conversations.json
```

---

## 3. CURRENT MEMORY FLOW

1. **Short-Term Memory**:
   - Held in `conversation_history` list (last 10 turns) inside `data/memory.json`.
   - Formatted into prompt context via `format_history_context()` (last 6 turns).
2. **Durable Memories**:
   - Stored in `memories` array inside `data/memory.json`.
   - Categorized into 6 structural categories: `PREFERENCE`, `FACT`, `PROJECT`, `PATTERN`, `PROGRESS`, `DECISION`.
   - Updated via `_upsert_memory()` which scores importance, frequency, confidence, and recency.
3. **Retrieval**:
   - `build_smart_memory_context()` filters memories by keyword relevance, active project, and active mode up to `MEMORY_CONTEXT_LIMIT` (6 items).
4. **Expiration / Freshness**:
   - No automatic TTL/expiration exists. Recency score decay is calculated based on `last_seen` timestamp.

---

## 4. CURRENT MODEL FLOW

Saki orchestrates 5 local Ollama models according to intent, task, and emotion:

| Model Tag | Model Name | Role / Intent | Selection Rule |
|---|---|---|---|
| `phi3:latest` | Phi-3 | Fast casual chat | Greetings, short chatter, low complexity |
| `nous-hermes2:latest` | Nous-Hermes 2 | Emotional support | Sadness, anxiety, loneliness, venting |
| `qwen3:8b` | Qwen 3 (8B) | General reasoning & default | Complex questions, deep thinking, general fallback |
| `qwen2.5-coder:7b` | Qwen 2.5 Coder | Code & Architecture | Code blocks, tracebacks, refactoring, building |
| `gemma3:4b` | Gemma 3 (4B) | Vision & Multimodal | Image attachments (`.png`, `.jpg`, `.webp`) |

- **Fallback**: If a specialist model fails, `model_manager.get_fallback_model()` routes to `qwen3:8b` (default).
- **Keep-Alive**: Managed via Ollama `keep_alive` parameter (default `5m`). `unload_model()` passes `keep_alive: 0` to release VRAM/RAM immediately.

---

## 5. CURRENT SEARCH FLOW

- **Primary Entry Point**: `backend/services/search_service.py` -> `safe_search(user_input)`.
- **Trigger**: Currently **helpless-response fallback only** (`is_helpless_response(full_response)` in `chat.py`). When the local model returns an "I don't know" or "cannot answer" response, Saki automatically triggers fallback search.
- **Privacy Enforcement**:
  - If `PRIVACY_MODE == "HIGH"`, `safe_search()` returns `[]` immediately (no external request made).
  - If `PRIVACY_MODE == "MEDIUM"`, `make_safe_query()` in `backend/core/privacy.py` prompts `call_model()` to strip all PII and sensitive user details before generating a neutral search query.
- **Search Execution**:
  - Calls `multi_search(query)` in `backend/services/search.py` (currently returning placeholder results).
  - Standalone legacy script `search.py` in root uses `google.generativeai` (Gemini 1.5 Flash).

---

## 6. CURRENT PRIVACY FLOW

Saki implements a multi-tier privacy configuration (`settings.PRIVACY_MODE`):
- `HIGH`: Fully private local mode. Outbound network search operations disabled.
- `MEDIUM`: Privacy-guarded mode (Default). Outbound queries pass through `make_safe_query()` to sanitize PII.
- `LOW`: Unrestricted external access.

### Privacy Audit Matrix:

| Data Type | Current Protection | Current Risk | Target Protection (Sprint 2+) |
|---|---|---|---|
| Name / Identity | Stripped by `make_safe_query()` in MEDIUM mode | Leakage if search skipped privacy gate | Strict PII Regex & Named Entity Redaction |
| Email / Phone / Address | Filtered by LLM prompt in `make_safe_query()` | Fail-open if LLM fails | Deterministic PII Scrubber |
| API Keys / Tokens | None in prompt | High if typed in user prompt | Fail-closed Secret Detector |
| System Prompts / Identity | Evaluator strips `[Instruction]` & system leaks | High if model echoes prompt | `ResponseEvaluator` Leak Gate (Implemented) |
| Personal Memories | Local JSON storage only | Leakage if sent to external API | Privacy Gate Context Filter |
| Code / File Paths | Stored in local attachments directory | Paths sent to LLM | Path Anonymizer Gate |

---

## 7. CURRENT EXTERNAL NETWORK FLOW

| Calling File | Function | Destination | Method | Data Sent | Data Received | Auth | Privacy Risk | Purpose |
|---|---|---|---|---|---|---|---|---|
| `ai_service.py` | `call_model()` | `http://localhost:11434/api/generate` | POST | Prompt JSON | Response JSON | None | None (Local) | Local LLM inference |
| `ai_service.py` | `stream_model()` | `http://localhost:11434/api/generate` | POST | Prompt JSON | Line stream | None | None (Local) | Streaming LLM inference |
| `model_manager.py` | `probe_ollama_status()` | `http://localhost:11434/api/tags` | GET | None | Model tags JSON | None | None (Local) | Model list inspection |
| `model_manager.py` | `probe_ollama_status()` | `http://localhost:11434/api/ps` | GET | None | Loaded models JSON | None | None (Local) | Loaded models inspection |
| `model_manager.py` | `unload_model()` | `http://localhost:11434/api/generate` | POST | `keep_alive: 0` | JSON | None | None (Local) | Force VRAM unload |
| `search.py` (root) | `multi_search()` | Google Gemini API (`generativeai`) | POST | Query string | Generated answer | Hardcoded API key | High | Legacy web search |
| `news_service.py` | `fetch_news()` | NewsAPI HTTP endpoint | GET | Topic query | News articles JSON | NewsAPI key | Medium | External news retrieval |
| `api.ts` (Frontend)| `fetchWithFallback()` | `http://127.0.0.1:8000/api/*` | GET/POST | Request payload | JSON / Stream | None | None (Local) | Frontend-Backend IPC |

---

## 8. CURRENT API INVENTORY

| Method | Path | Input Model | Output Model | Auth | Side Effects | External Access | Privacy Risk |
|---|---|---|---|---|---|---|---|
| `POST` | `/api/chat/stream` | `ChatRequest` | `StreamingResponse` | None | Updates memory & conversation threads | Optional (on helpless fallback) | Medium |
| `POST` | `/api/chat` | `ChatRequest` | `ChatResponse` | None | Updates memory & conversation threads | Optional (on helpless fallback) | Medium |
| `POST` | `/api/chat/unload` | Query `model_name` | JSON | None | Unloads model from VRAM | None (Local) | Low |
| `GET` | `/api/conversations` | None | `GroupedConversations` | None | Reads `conversations.json` | None (Local) | Low |
| `GET` | `/api/conversations/search` | Query `q` | JSON list | None | Reads `conversations.json` | None (Local) | Low |
| `GET` | `/api/conversations/{id}` | Path `conv_id` | `ConversationDetail` | None | Reads `conversations.json` | None (Local) | Low |
| `POST` | `/api/conversations/new` | None | `ConversationDetail` | None | Creates thread in `conversations.json` | None (Local) | Low |
| `DELETE`| `/api/conversations/{id}`| Path `conv_id` | JSON status | None | Deletes thread in `conversations.json` | None (Local) | Low |
| `GET` | `/api/memory` | None | `MemoryResponse` | None | Reads `memory.json` | None (Local) | Medium |
| `GET` | `/api/health` | None | `HealthResponse` | None | Probes Ollama & memory store | None (Local) | Low |
| `GET` | `/api/brain/status` | None | `BrainStatusData` | None | Reads model_manager & system resources | None (Local) | Low |
| `GET` | `/api/config` | None | `ConfigResponse` | None | Reads Settings constants | None (Local) | Low |
| `GET` | `/api/settings` | None | `AppSettings` | None | Reads `settings.json` | None (Local) | Low |
| `POST` | `/api/settings` | Body JSON | `AppSettings` | None | Writes `settings.json` | None (Local) | Low |
| `POST` | `/api/upload` | Multipart File | `ChatAttachment` | None | Writes file to `data/uploads/` | None (Local) | Medium |

---

## 9. CURRENT SECURITY FINDINGS

| Severity | File | Finding | Impact | Recommended Fix | Target Sprint |
|---|---|---|---|---|---|
| **HIGH** | `search.py` | Hardcoded Google Gemini API Key (`AIzaSy...`) | API key exposure in repository | Move to environment variable / `.env` | Sprint 1 |
| **MEDIUM** | `backend/main.py` | `CORSMiddleware` configured with `allow_origins=["*"]` | Cross-origin request forgery from local malicious web pages | Restrict origins to localhost/127.0.0.1 | Sprint 1 |
| **MEDIUM** | `chat.py: upload_file()` | No file extension / content-type validation | Arbitrary file upload to `data/uploads/` | Validate mime-types & sanitize file basenames | Sprint 1 |
| **LOW** | `search_service.py` | `make_safe_query()` relies on LLM to strip PII | Prompt injection could bypass PII sanitization | Add deterministic Regex PII pre-scrubber | Sprint 2 |

---

## 10. CURRENT TEST BASELINE

- **Test Framework**: Pytest (`pytest`)
- **Execution Command**: `python -m pytest backend/tests brain/tests -v`
- **Result**: **65 passed in 6.19s (100% pass rate)**
- **Coverage**:
  - `test_cognitive_state.py`: Task/stage inference & serialization
  - `test_conversations.py`: Thread creation & message appending
  - `test_emotional_intelligence.py`: Emotion analysis, social energy, active projects, awareness building
  - `test_learning_service.py`: Routing corrections & style preference learning
  - `test_memory_categories.py`: Memory categorization, extraction, retrieval, context building
  - `test_model_manager.py`: State machine transitions, telemetry recording, fallback routing
  - `test_orchestrator.py`: Intent routing across 5 models, frustration state handling
  - `test_persona.py`: System prompt construction, persona traits, anti-assistant rules
  - `test_response_evaluator.py`: Speaker tag cleansing, robotic cliche removal, internal leak sanitization
  - `test_response_planner.py`: Pre-generation strategy blueprint generation
  - `test_system_routes.py`: Health check, brain status, settings persistence, config endpoint
  - `test_chat_routes.py`: ChatRequest schema validation, history formatting, helplessness check, conversation CRUD
  - `test_privacy_search.py`: HIGH privacy mode search blocking, fallback privacy gate enforcement
  - `brain/tests/test_brain.py`: NLP normalizer, intent classification, complexity analysis, task planning, knowledge routing

---

## 11. EXISTING COMPONENTS THAT MUST BE REUSED

- `SakiModelOrchestrator` (`backend/services/orchestrator.py`): Core decision engine for request classification.
- `SakiAwareness` & `EmotionalState` (`backend/services/emotional_intelligence.py`): Emotion & posture tracker.
- `ResponsePlanner` (`backend/services/response_planner.py`): Strategic blueprint builder.
- `ResponseEvaluator` (`backend/services/response_evaluator.py`): Leak & cliche sanitizer gate.
- `ModelManager` (`backend/services/model_manager.py`): Model state machine & telemetry recorder.
- `memory_service` (`backend/services/memory_service.py`): Categorized durable memory store.
- `privacy.py` (`backend/core/privacy.py`): Safe query transformer.

---

## 12. COMPONENTS THAT MUST NOT BE DUPLICATED

- Do NOT create a second model router; extend `SakiModelOrchestrator`.
- Do NOT create a second memory file; extend `data/memory.json` schemas.
- Do NOT bypass `ResponseEvaluator`; all world-access responses must pass through the evaluator quality gate.
- Do NOT bypass `ModelManager`; telemetry must track external intelligence execution overhead.

---

## 13. WORLD ACCESS INTEGRATION POINTS

```
[ User Input ]
      │
      ▼
SakiModelOrchestrator.classify_request()
      │
      ├── (Current: CHAT, SUPPORT, BUILDER, THINKING, VISION)
      └── (Future Integration Point: WEB_SEARCH, WEB_FETCH, RESEARCH, BROWSER)
            │
            ▼
   [ WorldAccessManager ]  <── Integrated in Sprint 1
            │
            ├── PrivacyGate.sanitize_query()  <── Integrated in Sprint 2
            ├── SearchProvider / WebFetcher   <── Integrated in Sprint 3
            └── EvidenceEngine.assemble()     <── Integrated in Sprint 4
```

---

## 14. FUTURE ACTION TAXONOMY (DESIGN CONTRACT)

| Action Type | Purpose | When to Use | Privacy Level | User Confirmation |
|---|---|---|---|---|
| `LOCAL_REASONING` | Pure LLM inference | Internal logic, coding, casual chat | `PUBLIC` / `LOCAL` | No |
| `MEMORY_RECALL` | Retrieve user memories | Questions about user preferences/past | `LOCAL` | No |
| `RAG_RETRIEVAL` | Retrieve local documents | Inquiries about uploaded files | `LOCAL` | No |
| `WEB_SEARCH` | Execute web search query | Real-time information, facts, news | `CONTEXTUAL` | No (if Privacy Gate passes) |
| `WEB_FETCH` | Extract content from URL | User provides direct URL link | `CONTEXTUAL` | No |
| `WEB_RESEARCH` | Deep multi-query research | Complex research topics | `CONTEXTUAL` | No |
| `BROWSER_READ` | Read DOM / page state | Interacting with dynamic web apps | `RESTRICTED` | Required in Privacy Mode HIGH |
| `BROWSER_INTERACT`| Form submission / click | Autonomous browser actions | `SECRET` / `RESTRICTED` | Always Required |

---

## 15. FUTURE PRIVACY CLASSIFICATION (DESIGN CONTRACT)

1. `PUBLIC`: General facts, public documentation, non-sensitive queries. Safe for external search.
2. `CONTEXTUAL`: Project names, general technical context. Sanitized before external transmission.
3. `PERSONAL`: User preferences, non-sensitive habits. Stripped before external transmission.
4. `PRIVATE`: User's full name, location, contact info, personal relationships. **NEVER transmitted externally**.
5. `SECRET`: Passwords, API keys, tokens, credentials, private code keys. **NEVER transmitted externally; triggers immediate fail-closed gate**.
6. `RESTRICTED`: Local filesystem paths, system environment variables. Stripped or blocked.

---

## 16. FUTURE EVIDENCE CONTRACT (DESIGN CONTRACT)

Conceptual Evidence Schema for Sprint 4:

```python
class EvidenceItem(BaseModel):
    source_type: str  # "search_result", "web_page", "document", "news_article"
    url: Optional[str] = None
    domain: Optional[str] = None
    title: str
    content: str
    retrieved_at: float
    published_at: Optional[float] = None
    freshness_score: float = 1.0  # 0.0 to 1.0
    relevance_score: float = 1.0  # 0.0 to 1.0
    authority_score: float = 1.0  # 0.0 to 1.0
    confidence: float = 1.0       # 0.0 to 1.0
    provenance: Dict[str, Any] = Field(default_factory=dict)
```

---

## 17. FUTURE MEMORY INTEGRATION CONTRACT

- **World Knowledge vs User Memory**: External web search results will be flagged with `source: "world_access"` and `type: "WORLD_KNOWLEDGE"` to prevent confusing web facts with user personal memories.
- **Expiration / TTL**: Web knowledge evidence will carry a `ttl_seconds` property (default 86,400s / 24h) after which it is marked stale.

---

## 18. FUTURE BROWSER INTEGRATION CONTRACT

- All autonomous browser interaction (`BROWSER_INTERACT`) will mandate explicit user confirmation dialog in the UI before execution.
- Read-only DOM extraction (`BROWSER_READ`) will execute inside an isolated headless context without session cookie persistence unless authorized.

---

## 19. FUTURE SECURITY REQUIREMENTS

1. **SSRF Prevention**: All outbound URL fetches must resolve IP addresses and block private/loopback ranges (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `169.254.169.254`).
2. **Prompt Injection Boundary**: Web content fetched from external sites must be wrapped inside `<external_web_content>` tags with explicit system instructions to ignore embedded instructions.
3. **Secret Redaction**: ResponseEvaluator gate will be updated with Regex secret detection rules to block inadvertent credential leaks.

---

## 20. SPRINT 1 REQUIREMENTS (COGNITIVE ACTION ENGINE CONTRACT)

Sprint 1 will implement the **Cognitive Action Engine**:
1. Refactor `SakiModelOrchestrator` to emit formal `ActionPlan` objects (`action_type`, `queries`, `urls`, `confidence`, `requires_world_access`).
2. Implement `ActionDecisionEngine` to decide whether a user query can be answered locally or requires `WEB_SEARCH`.
3. Wire `ActionPlan` into `chat.py` pipeline without breaking existing local chat functionality.
4. Add unit test suite for action classification.
