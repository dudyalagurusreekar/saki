# Saki System Baseline & Stabilization Audit (Sprint 0)
**Audit Date:** August 19, 2026  
**Repository Branch:** `p1`  
**Host Environment:** Windows 11, NVIDIA GeForce RTX 5060 Laptop GPU (8GB VRAM), Python 3.12, Node.js / Next.js 15.5.15, Ollama v0.x

---

## 1. Current Architecture Overview

Saki is designed as a hybrid AI companion consisting of:
1. **FastAPI Backend (`backend/main.py`)**: Runs on `http://127.0.0.1:8000`. Exposes REST and SSE streaming endpoints for chat, conversations, memory, telemetry, and system health.
2. **Next.js Frontend (`frontend/src/`)**: Runs on `http://127.0.0.1:3000`. Full React/Tailwind/Lucide UI with Dynamic Sky Background, TopBar HUD, Multi-session Sidebar, Chat Window, Brain Telemetry Panel, and Memory/Settings modals.
3. **Local Ollama Integration (`backend/services/ai_service.py`)**: Communicates with Ollama running locally at `http://127.0.0.1:11434` for 5 local model weights.
4. **World Access & Grounding Subsystem (`backend/services/world_access_manager.py`, `gemini_search.py`, `evidence_engine.py`)**: Controlled external web retrieval with SSRF guard, relevance scoring, and factual verification.
5. **Memory Subsystem (`backend/services/memory_service.py`, `data/memory.json`, `data/conversations.json`)**: Persistent JSON storage for conversation turns, categorized memories (projects, preferences, decisions, facts, progress), and emotional state awareness.
6. **Legacy CLI Entrypoints (`chat.py`, `search.py`, `proactive.py`)**: Standalone terminal scripts with legacy Piper voice synthesis and Google STT.

```
[ Next.js Frontend (port 3000) ]
        │
        ▼ HTTP / SSE / REST
[ FastAPI Backend (port 8000) ] 
        ├── Router: /api/chat, /api/chat/stream, /api/conversations, /api/memory, /api/health, /api/brain/status
        ├── Model Orchestrator & Action Engine (Deterministic Routing)
        ├── Saki Persona & Cognitive State
        ├── Privacy Policy Engine (Gatekeeper / Fail-Closed)
        ├── Memory & Personal Context Service (JSON persistence)
        ├── Ollama Local Model Hub (5 Models: Phi-3, Hermes-2, Qwen-3, Qwen-Coder, Gemma-3)
        └── World Access Manager (Gemini Grounded Search / DuckDuckGo / Evidence Engine)
```

---

## 2. Component Status Audit

### Backend Status
* **Status:** `OPERATIONAL`
* **Entrypoint:** `backend/main.py`
* **CORS:** Configured for `http://localhost:3000`.
* **Startup Time:** ~0.50s (FastAPI + Uvicorn).
* **Endpoints:**
  - `GET /`: Root heartbeat (`"status": "running"`).
  - `GET /api/health`: Full health probe reporting Ollama connection, available models, loaded models, and memory status.
  - `GET /api/brain/status`: Telemetry data for model, mode, token metrics, hardware resources, and awareness.
  - `GET /api/conversations`, `GET /api/conversations/{id}`, `POST /api/conversations/new`, `DELETE /api/conversations/{id}`: Conversation thread CRUD.
  - `GET /api/memory`: Memory categorization retrieval.
  - `POST /api/chat`: Non-streaming full response generation with orchestrator decision metadata.
  - `POST /api/chat/stream`: Server-Sent Events (SSE) token-by-token streaming.
  - `POST /api/chat/unload`: Manual Ollama model VRAM eviction.
  - `POST /api/upload`: Multi-format file attachment parsing (PDF, DOCX, TXT, images).

### Frontend Status
* **Status:** `OPERATIONAL`
* **Framework:** Next.js 15.5.15 (App Router), React 19, TypeScript, TailwindCSS.
* **Startup Time:** Ready in 3.5s (`npm run dev`).
* **Components:**
  - `SkyBackground.tsx`: Dynamic gradient sky rendering based on diurnal time-of-day.
  - `TopBar.tsx`: System status, active model, mode indicator, latency metrics, and action buttons.
  - `Sidebar.tsx`: Multi-conversation management grouped by Today, Yesterday, and Older with real-time search.
  - `ChatWindow.tsx`: Main chat layout with message history, live streaming renderer, and modal managers.
  - `BrainPanel.tsx`: Flyout drawer displaying cognitive state, latency breakdowns, VRAM usage, and emotional radar.
  - `InputBox.tsx`: Multi-line prompt input, attachment drawer, and send triggers.
  - `MemoryModal.tsx`, `SettingsModal.tsx`: Configuration and memory inspection dialogs.

### Chat & Streaming Status
* **Basic Text Chat (`POST /api/chat`):** `OPERATIONAL`. Successfully selects model (e.g. `phi3:latest`), applies unified persona guidelines, generates contextual answers, and records turn to memory.
* **Streaming Chat (`POST /api/chat/stream`):** `OPERATIONAL`. Streams tokens over SSE protocol directly to frontend or HTTP clients with chunk-level delivery.

### Model Status (5 Configured Models)
All 5 target models are verified locally installed in Ollama:
1. `phi3:latest` (2.2 GB) — Casual mode, fast responses, query normalization.
2. `nous-hermes2:latest` (6.1 GB) — Support/emotional mode, empathetic dialogue.
3. `qwen3:8b` (5.2 GB) — Thinking mode, complex reasoning, general default.
4. `qwen2.5-coder:7b` (4.7 GB) — Builder mode, code generation, refactoring.
5. `gemma3:4b` (3.3 GB) — Vision inspection, image analysis.

### Memory & Personal Context Status
* **Status:** `OPERATIONAL`
* **Storage:** Local files `data/memory.json` and `data/conversations.json`.
* **Capabilities:** Smart memory context builder limits recent turns, tracks active user projects, emotional history, and categorizes admitted preferences vs request-scoped ephemeral facts.

### RAG & Knowledge Graph Status
* **Status:** `PARTIALLY IMPLEMENTED (In-Memory Stubs & Subgraph Builders)`
* Modules `unified_knowledge.py`, `knowledge_fusion.py`, and `knowledge_graph.py` provide structured interfaces and graph traversal, though deep vector embeddings are currently mocked.

### Voice & TTS Status
* **Status:** `LEGACY CLI ONLY / ABSENT IN WEB BACKEND`
* **Implementation:**
  - Hardcoded in root `chat.py` (lines 20-25, 61-79).
  - Invokes `D:\applications\piper\piper.exe` via shell pipe.
  - Generates `D:\applications\piper\temp.wav`.
  - Plays audio synchronously via PowerShell `(New-Object Media.SoundPlayer ...).PlaySync()`, which blocks thread execution until speech ends.
  - Voice input uses Google STT `speech_recognition.Recognizer.recognize_google()`.
  - **Backend API:** No audio/speech route or Piper wrapper currently exists in `backend/`.

### Vision Status
* **Status:** `STRUCTURAL SUPPORT READY / BACKEND INTEGRATED`
* Attachment handling in `backend/routes/chat.py` accepts image files, routes requests to `gemma3:4b` when vision keywords or image attachments are present, and passes image references to model prompts.

### Web & World-Access Status
* **Status:** `OPERATIONAL (Controlled)`
* **Providers:**
  - Google Gemini Search Grounding (`backend/services/gemini_search.py`).
  - DuckDuckGo HTML scraping fallback (`backend/services/world_access_manager.py`).
  - Strict SSRF Guard blocking loopback, RFC1918 private IPs, and cloud metadata endpoints (`169.254.169.254`).
  - Factual grounding verifier and source authority scoring engine.

---

## 3. Privacy & External Network Behavior Matrix

Every component interacting with I/O is classified below:

| Component / Subsystem | Classification | External Destination | Notes |
| :--- | :--- | :--- | :--- |
| `backend/services/ai_service.py` | `LOCAL` | None (`127.0.0.1:11434`) | Local Ollama HTTP daemon |
| `backend/services/orchestrator.py` | `LOCAL` | None | Pure heuristic routing engine |
| `backend/services/model_manager.py` | `LOCAL` | None (`127.0.0.1:11434`) | Ollama process & VRAM control |
| `backend/services/memory_service.py` | `LOCAL` | None | Disk storage (`data/memory.json`) |
| `backend/core/privacy.py` | `LOCAL` | None | Fail-closed regex secret and PII filter |
| `backend/core/saki_persona.py` | `LOCAL` | None | System prompt construction |
| `backend/services/gemini_search.py` | `EXTERNAL` | `generativelanguage.googleapis.com` | Google Search grounding API call |
| `backend/services/world_access_manager.py` | `EXTERNAL / OPTIONAL` | `html.duckduckgo.com` | Fallback web search scraper |
| `backend/services/evidence_engine.py` | `LOCAL` | None | In-memory evidence normalization |
| `backend/services/grounding_verifier.py` | `LOCAL` | None | Deterministic verification logic |
| `backend/services/source_trust_engine.py` | `LOCAL` | None | Static domain authority database |
| `backend/services/news_service.py` | `EXTERNAL / OPTIONAL` | `newsapi.org` | News endpoint (fallback stub if no key) |
| `backend/services/git_github_capability.py`| `EXTERNAL / OPTIONAL` | `api.github.com` | Remote repo operations if token supplied |
| `backend/services/web_controller.py` | `EXTERNAL` | Public HTTP/HTTPS target URLs | Fetches webpage contents subject to SSRF |
| `chat.py` (root legacy script) | `EXTERNAL` | `google.com` (STT) | Google Speech-to-Text API |
| `search.py` (root legacy script) | `EXTERNAL` | `generativelanguage.googleapis.com` | Legacy direct Gemini API call |

---

## 4. Component Classification Matrix

```
[ KEEP ]
- backend/main.py
- backend/core/config.py
- backend/core/privacy.py
- backend/core/saki_persona.py
- backend/core/saki_state.py
- backend/models/schemas.py
- backend/routes/chat.py
- backend/routes/system.py
- backend/routes/memory.py
- backend/services/ai_service.py
- backend/services/orchestrator.py
- backend/services/model_manager.py
- backend/services/memory_service.py
- backend/services/memory_admission.py
- backend/services/emotional_intelligence.py
- backend/services/personal_context.py
- backend/services/response_planner.py
- backend/services/response_evaluator.py
- backend/services/learning_service.py
- backend/services/world_access_manager.py
- backend/services/gemini_search.py
- backend/services/evidence_engine.py
- backend/services/grounding_verifier.py
- backend/services/source_trust_engine.py
- backend/services/temporal_service.py
- frontend/src/app/* (layout, page, providers, globals)
- frontend/src/components/ChatWindow.tsx
- frontend/src/components/TopBar.tsx
- frontend/src/components/Sidebar.tsx
- frontend/src/components/BrainPanel.tsx
- frontend/src/components/InputBox.tsx
- frontend/src/components/MessageBubble.tsx
- frontend/src/components/SkyBackground.tsx
- frontend/src/components/MemoryModal.tsx
- frontend/src/components/SettingsModal.tsx
- frontend/src/lib/api.ts

[ MODIFY LATER ]
- requirements.txt (install missing psutil, cleanup redundant deps)
- backend/services/unified_knowledge.py (upgrade from in-memory stubs to local vector index)
- backend/services/knowledge_fusion.py
- backend/services/knowledge_graph.py
- backend/services/adaptive_intelligence.py
- backend/services/autonomous_workflow.py
- backend/services/browser_controller.py
- backend/services/computer_controller.py
- backend/services/development_capability.py
- backend/services/task_capability.py
- backend/services/web_controller.py
- backend/services/web_intelligence.py
- backend/tests/test_relevance_gate.py
- backend/tests/test_web_pipeline.py
- backend/tests/test_evidence_intelligence.py
- backend/tests/test_gemini_search.py

[ REPLACE LATER ]
- chat.py (replace legacy CLI with unified client or backend TTS/STT services)
- search.py (replace with backend world access manager)
- news.py / backend/news.py (replace with unified news provider)

[ OPTIONAL ]
- proactive.py (background proactive cron service)
- tests/reliability/* (diagnostic scripts suite)

[ BROKEN ]
- tests/reliability/test_quotas.py (executes live network request during module import)
- frontend/src/components/chat/* (legacy duplicated unused component directory)

[ UNKNOWN ]
- app/ directory (vestigial alternative entrypoint with empty services)
- brain/ directory (standalone rule & parser modules partially mirrored in backend)
```

---

## 5. Baseline Performance Measurements

| Metric | Measured Baseline Value | Context / Conditions |
| :--- | :--- | :--- |
| **Backend Startup Time** | `~0.50 s` | Uvicorn + FastAPI initialization on localhost:8000 |
| **Frontend Ready Time** | `~3.50 s` | Next.js 15 App Router on localhost:3000 |
| **LLM Response Latency (Non-streaming)** | `~12.4 s` | `phi3:latest` casual mode initial query |
| **First-Token Latency (Streaming)** | `~20.9 s` | `phi3:latest` cold start streaming query |
| **Total Streaming Duration** | `~24.7 s` | 196 token stream output |
| **GPU Model & VRAM Total** | `NVIDIA GeForce RTX 5060 Laptop (8151 MiB)` | Windows 11 WDDM driver 610.88, CUDA 13.3 |
| **VRAM Usage (Idle with Model)** | `4650 MiB / 8151 MiB (~57%)` | Allocated by `llama-server.exe` |
| **TTS Latency (Legacy Piper)** | `~1.2 - 2.8 s (Blocking)` | CLI PowerShell synchronous `.PlaySync()` |

---

## 6. Test Suite Baseline Findings

* **Unit Test Framework:** Pytest 9.1.1 on Python 3.12.10.
* **Execution Results (`backend/tests`):**
  - **Total Tests:** 216
  - **Passed:** 209 (96.8%)
  - **Failed:** 7 (3.2%)
  - **Warnings:** 233 (Pydantic V2 `.dict()` deprecation notices and TestClient HTTP warnings).
* **Test Failure Root Causes:**
  1. `test_evidence_synthesis_and_grounded_prompt_block`: Strict string matching against evidence template header.
  2. `test_gemini_disabled_returns_failure_stub`: Mock expectation mismatch when Gemini is disabled.
  3. `test_kambadur_temple_relevance_matching`, `test_uncertain_results_fail_closed`, `test_kambadur_refusal_on_unrelated_search_results`, `test_vijayawada_places_filtering`, `test_unknown_entity_refusal`: Strict keyword/token-overlap relevance thresholding on Indian geographical entities.
* **Isolation Note:** `brain/tests/test_brain.py` passed 12/12 tests (100%).

---

## 7. Known Bugs & Architecture Limitations

1. **Voice Pipeline Unintegrated:** Voice input/output exists only in `chat.py` CLI and is completely disconnected from the Web UI / FastAPI backend.
2. **Blocking Audio Playback:** Piper TTS in `chat.py` uses blocking PowerShell audio playback, freezing thread execution while Saki is speaking.
3. **Pydantic V2 Deprecation Warnings:** Multiple services call `.dict()` instead of `.model_dump()`.
4. **Duplicate Directories:** 
   - `app/` vs `backend/` vs `brain/`
   - `frontend/src/components/chat/` vs `frontend/src/components/`
   - `news.py` (root), `backend/news.py`, `backend/services/news_service.py`
5. **Hardcoded API Key in Legacy Root Files:** Root `search.py` contains hardcoded legacy key strings; modern pipeline in `backend/` correctly uses environment variables.
6. **Live Network Calls in Test Collection:** `tests/reliability/test_quotas.py` performs synchronous HTTP requests at module import time instead of inside test fixtures.

---

## 8. Future Integration Points

* **Voice / Piper Streaming Service:** Create a dedicated FastAPI endpoint `/api/voice/tts` and `/api/voice/stt` using non-blocking background workers and Web Audio API in the frontend.
* **HUD Voice Visualization:** Dock an audio waveform / state orb inside `frontend/src/components/TopBar.tsx`.
* **Saki Core Avatar / Presence Canvas:** Integrate visual avatar rendering directly onto `frontend/src/components/SkyBackground.tsx` and central chat canvas.
* **Brain Panel Telemetry Stream:** Connect WebSocket or polling endpoint from `frontend/src/components/BrainPanel.tsx` to `/api/brain/status`.
