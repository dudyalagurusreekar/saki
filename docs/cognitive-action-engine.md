# Saki AI — Cognitive Action Engine Architecture & Specification
**Sprint 1 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Local Executive Decision Layer  

---

## 1. PURPOSE

The Cognitive Action Engine serves as Saki's executive capability decision subsystem. It evaluates incoming user requests, context, freshness requirements, and attachments to produce a strongly typed `ActionDecision` blueprint.

The Action Engine decouples capability determination (`WHAT to do`) from execution (`HOW to do it`). In Sprint 1, all capability decisions are evaluated locally using a hybrid decision matrix without making external tool or network calls.

---

## 2. ARCHITECTURE

```
                  [ User Input / ChatRequest ]
                                │
                                ▼
         [ backend.services.orchestrator.classify_request() ]
                                │
                                ▼
         [ backend.services.action_engine.decide_action() ]
              ├── 1. Explicit Intent & URL Detection
              ├── 2. Attachment / Vision Check
              ├── 3. Information Freshness Classification
              ├── 4. Memory & RAG Relevance Check
              ├── 5. Knowledge Uncertainty vs Freshness Matrix
              └── 6. Multi-Action Sequence Generator
                                │
                                ▼
                      [ ActionDecision Object ]
                                │
             ┌──────────────────┴──────────────────┐
             ▼                                     ▼
[ LOCAL_REASONING / MEMORY_RECALL ]     [ WEB_SEARCH / BROWSER_* ]
  (Processed via Local LLMs)            (Recorded; Execution deferred
                                         to Sprint 2+ World Access)
```

---

## 3. ACTION TAXONOMY

Saki defines 12 core capability actions:

| Action Tag | Purpose | When to Select | Future Executor | Status |
|---|---|---|---|---|
| `LOCAL_REASONING` | Local LLM inference | General chat, stable knowledge, coding theory | Phi-3 / Qwen-3 | Implemented |
| `MEMORY_RECALL` | Retrieve user memories | Questions about user preferences or past turns | MemoryService | Implemented |
| `RAG_RETRIEVAL` | Retrieve document knowledge | Questions about uploaded PDFs/files | Local Vector Store | Implemented |
| `WEB_SEARCH` | Retrieve current public facts | Time-sensitive questions, explicit "search online" | WorldAccessManager | Decision Implemented (Execution Deferred) |
| `WEB_FETCH` | Extract content from URL | User provides explicit URL link | WebFetcher | Decision Implemented (Execution Deferred) |
| `WEB_RESEARCH` | Deep multi-source research | Multi-source synthesis or comparison requests | EvidenceEngine | Decision Implemented (Execution Deferred) |
| `BROWSER_READ` | Inspect webpage DOM | Reading dynamic web page structures | Headless Browser | Decision Implemented (Execution Deferred) |
| `BROWSER_INTERACT` | Form submit or click | Interactive website navigation | Headless Browser | Decision Implemented (Requires Auth in Sprint 5) |
| `VISION` | Multimodal image inspection | Image attachments or visual layout questions | Gemma 3 (4B) | Implemented |
| `CODING` | Code syntax & debugging | Scripting, tracebacks, refactoring, implementation | Qwen 2.5 Coder | Implemented |
| `CLARIFICATION` | Request user clarification | Ambiguous or low-confidence queries (<0.55) | Local LLM | Implemented |
| `NO_ACTION` | No capability required | System ping or silent acknowledgment | None | Implemented |

---

## 4. DECISION PIPELINE

1. **Normalize Input**: Strip whitespace, extract attachments.
2. **Explicit Intent Detection**: Match keywords ("search online", "read webpage url", "remember my preference").
3. **Freshness Classification**: Categorize requirement (`STABLE`, `CURRENT`, `LIVE`, `USER_EXPLICIT_SEARCH`, `UNKNOWN`).
4. **Local-First Priority Evaluation**:
   `Context -> Memory -> RAG -> Web -> Browser -> Vision -> Coding`.
5. **Uncertainty Matrix**:
   - `UNKNOWN` + `STABLE` = `LOCAL_REASONING` or `CLARIFICATION`
   - `UNKNOWN` + `CURRENT` = `WEB_SEARCH` / `WEB_RESEARCH`
6. **Multi-Action Planning**: Generate `planned_actions` array (e.g. `["MEMORY_RECALL", "WEB_RESEARCH", "LOCAL_REASONING"]`).
7. **Confidence & Fallback**: Calculate confidence score (0.0 to 1.0). If confidence < 0.55 or exception occurs, return safe fallback decision (`LOCAL_REASONING`).

---

## 5. FRESHNESS LOGIC MATRIX

- **`STABLE`**: Fundamental concepts, algorithms, math (e.g. "What is a binary search tree?").
- **`CURRENT`**: Software versions, current news, recent facts (e.g. "What is the latest Python version in 2026?").
- **`LIVE`**: Weather, live stock prices, status checks (e.g. "Current weather in Tokyo").
- **`USER_EXPLICIT_SEARCH`**: User explicitly requests web search (e.g. "Search online for PyTorch CUDA compatibility").
- **`UNKNOWN`**: Ambiguous freshness requirement.

---

## 6. MEMORY INTERACTION

- `ActionEngine` detects memory queries (`MEMORY_RECALL`) using regex patterns without loading the entire memory database into the prompt.
- Memory retrieval remains governed by `backend.services.memory_service`. `ActionEngine` does NOT write or overwrite durable memories directly.

---

## 7. RAG INTERACTION

- `ActionEngine` detects document queries (`RAG_RETRIEVAL`) when attachments contain `.pdf`, `.docx`, or `.txt` files, or when the query explicitly references uploaded documents.

---

## 8. FUTURE WORLD ACCESS INTERACTION

For `WEB_SEARCH`, `WEB_FETCH`, `WEB_RESEARCH`, `BROWSER_READ`, and `BROWSER_INTERACT`:
- In Sprint 1, `ActionEngine` generates the `ActionDecision` object with `requires_world_access = True`.
- **No external HTTP/SearXNG calls are made**. The local LLM handles the response gracefully while recording telemetry.

---

## 9. MULTI-ACTION PLANNING

For complex multi-step queries:
- Query: *"Using my previous project decisions, compare multi-source current frameworks"*
- Generated `planned_actions`: `["MEMORY_RECALL", "WEB_RESEARCH", "LOCAL_REASONING"]`

---

## 10. CONFIDENCE & ERROR HANDLING

- Threshold: `CONFIDENCE_THRESHOLD = 0.55`.
- Low-confidence queries (<0.55) route to `CLARIFICATION`.
- Exceptions during decision pipeline trigger `decision_status = "FALLBACK"` and return `LOCAL_REASONING`.

---

## 11. SECURITY MODEL

1. **No External Calls**: Action Engine runs 100% locally.
2. **No Secret Exposure**: Credentials/tokens are never processed or output.
3. **No Hidden Chain-of-Thought**: `reason` contains only concise summaries. No raw model deliberation traces are stored.
4. **No Arbitrary Execution**: Action decision object is a data contract, not an executable function.

---

## 12. EXAMPLES

```json
{
  "action": "WEB_SEARCH",
  "reason": "Request requires fresh, current, or time-sensitive public information.",
  "confidence": 0.95,
  "requires_memory": false,
  "requires_rag": false,
  "requires_world_access": true,
  "requires_fresh_information": true,
  "requires_user_confirmation": false,
  "query_intent": "current_information",
  "task_type": "information_request",
  "information_need": "latest_public_data",
  "priority": "normal",
  "fallback_action": "LOCAL_REASONING",
  "freshness_requirement": "CURRENT",
  "planned_actions": ["WEB_SEARCH", "LOCAL_REASONING"],
  "decision_status": "SUCCESS"
}
```
*(NOT IMPLEMENTED IN SPRINT 1: External execution of WEB_SEARCH)*
