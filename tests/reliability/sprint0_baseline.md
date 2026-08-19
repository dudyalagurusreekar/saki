# Saki Sprint 0 Diagnostic Test Specification

This document defines the baseline test specification for evaluating Saki's current behavior across 13 core categories (A through M) on branch `p1` (commit `3a57e8d`).

## Test Environment Setup
- **Branch**: `p1`
- **Commit**: `3a57e8d`
- **Models Loaded**: `phi3:latest`, `nous-hermes2:latest`, `qwen3:8b`, `qwen2.5-coder:7b`, `gemma3:4b` via local Ollama (`http://localhost:11434`)
- **Web Search Provider**: `GeminiSearchProvider` (`GEMINI_API_KEY` loaded from `.env`)

---

## CATEGORY A — CASUAL CONVERSATION
Evaluates everyday banter, greeting recognition, lightweight routing, and persona behavior without unnecessary web or memory access.

1. **A1**: `"Hey Saki"`
2. **A2**: `"How are you?"`
3. **A3**: `"Tell me something interesting."`
4. **A4**: `"Good morning Saki."`

**Inspection Criteria**:
- Selected model (Expect lightweight: `phi3:latest`).
- Task type / Mode (Expect: `simple_chat` / `casual`).
- Web Access triggered (Expect: `False`).
- Persona and verbosity (Expect concise, warm, natural response).

---

## CATEGORY B — GENERAL KNOWLEDGE
Evaluates stable conceptual explanation routing and model knowledge utilization without unnecessary web retrieval.

1. **B1**: `"What is FastAPI?"`
2. **B2**: `"What is overfitting?"`
3. **B3**: `"Explain transformers in machine learning."`
4. **B4**: `"What is the difference between RAM and VRAM?"`

**Inspection Criteria**:
- Web Access requirement (Expect: `False` / `LOCAL_REASONING`).
- Selected model (Expect: `qwen3:8b`).
- Factual quality and clarity of explanation.
- Absence of unnecessary web search context.

---

## CATEGORY C — CURRENT / FRESH INFORMATION
Evaluates time-sensitive web search triggers, provider transparency, and live evidence processing.

1. **C1**: `"What is the latest Python version?"`
2. **C2**: `"What is the latest version of FastAPI?"`
3. **C3**: `"What are the latest developments in AI?"`
4. **C4**: `"What is happening in technology right now?"`

**Inspection Criteria**:
- Web Access requirement (Expect: `True` / `WEB_SEARCH`).
- Provider status & error detail (`GeminiSearchProvider` HTTP/API status).
- Evidence processing and final answer accuracy.
- Verification whether stale model weights are presented as current facts.

---

## CATEGORY D — LOCAL / OBSCURE ENTITY
Evaluates entity resolution, location checks, and hallucination prevention on regional heritage or local entities.

1. **D1**: `"What is special about Kambadur Temple in Andhra Pradesh?"`
2. **D2**: `"Who built Kambadur Temple?"`
3. **D3**: `"What are special places in Vijayawada?"`
4. **D4**: `"Tell me about Lepakshi Temple in Andhra Pradesh."`

**Inspection Criteria**:
- Entity keyword identification in `RelevanceGate`.
- Relevance decisions (`RELEVANT` vs `IRRELEVANT`).
- Exclusion of unrelated locations/towns (e.g. Yelahanka Fort, Tadipatri).
- Detection of hallucinated deities, rivers, districts, or builders.

---

## CATEGORY E — NO / INSUFFICIENT EVIDENCE
Evaluates fail-closed behavior, refusal directives, and refusal response accuracy when querying non-existent or unevidenced entities.

1. **E1**: `"Tell me about XYZ12345 Temple in Andhra Pradesh."`
2. **E2**: `"Who built the ancient fort of FooBarBaz in 1421?"`
3. **E3**: `"What is special about the village of QuxQuuxZapr in India?"`

**Inspection Criteria**:
- `EvidencePackage.evidence_status` (Expect: `INSUFFICIENT`).
- Refusal directive injection in system prompt.
- Response acknowledgment of insufficient evidence without inventing details.

---

## CATEGORY F — AMBIGUOUS ENTITY
Evaluates entity disambiguation and project vs external entity resolution.

1. **F1**: `"Tell me about Saki."`
2. **F2**: `"Tell me about Python."`
3. **F3**: `"Tell me about Gemini."`

**Inspection Criteria**:
- Whether Saki asks for clarification or chooses a reasonable interpretation.
- Distinguishing user's Saki project from anime/external entities.
- Unnecessary web search vs project memory check.

---

## CATEGORY G — PERSONAL MEMORY
Evaluates user preference and personal fact extraction, storage, and retrieval without leaking test data.

1. **G1**: `"My favorite test project is Project Aurora."`
2. **G2**: `"What is my favorite test project?"`

**Inspection Criteria**:
- Memory admission decision and type (`PREFERENCE` / `FACT`).
- Storage in `data/memory.json`.
- Context retrieval in `build_smart_memory_context`.

---

## CATEGORY H — PROJECT MEMORY
Evaluates active project tracking and project-specific memory context isolation.

1. **H1**: `"I am currently working on Project Aurora."`
2. **H2**: `"What project am I working on?"`
3. **H3**: `"What were we working on?"`

**Inspection Criteria**:
- Active project update in `SakiAwareness`.
- Memory extraction (`PROJECT` type).
- Accuracy of project recall in subsequent turns.

---

## CATEGORY I — DECISION MEMORY
Evaluates technical decision recording and retrieval.

1. **I1**: `"We decided to use Gemini for web grounding in Project Aurora."`
2. **I2**: `"What did we decide for web grounding?"`

**Inspection Criteria**:
- Memory type classification (`DECISION`).
- Retrieval ranking in `retrieve_memories`.
- Response accuracy citing the exact recorded decision.

---

## CATEGORY J — CONFLICTING INFORMATION
Evaluates contradiction detection and source comparison handling in verification mode.

1. **J1**: `"Does the government support heritage maintenance for Kambadur Temple?"` (Simulated conflicting source snippets)

**Inspection Criteria**:
- `ConflictDetector` detection of direct/temporal contradictions.
- Claim support status in `EvidencePackage`.
- Saki's explicit acknowledgment of uncertainty or source conflicts.

---

## CATEGORY K — CODING
Evaluates Builder mode routing, code parsing, and programming error explanation.

1. **K1**: `"Explain this Python error: NameError: name 'x' is not defined"`
2. **K2**: `"Write a Python function to reverse a string."`
3. **K3**: `"Why does this code fail: def add(a, b): return a + c"`

**Inspection Criteria**:
- Routing model (Expect: `qwen2.5-coder:7b`).
- Conversation mode (Expect: `builder`).
- Web access requirement (Expect: `False`).
- Code syntax correctness and explanation quality.

---

## CATEGORY L — EMOTIONAL / SUPPORT
Evaluates emotional state analysis, empathetic tone modulation, and Support mode routing.

1. **L1**: `"I'm frustrated because my project isn't working."`

**Inspection Criteria**:
- Detected emotion (Expect: `frustrated`, intensity >= 0.75).
- Routing decision (Expect: `nous-hermes2:latest` / `support`).
- Tone guidance (warmth, empathy, absence of robotic cliches).

---

## CATEGORY M — STREAMING VS NORMAL CHAT
Compares execution pipeline, model selection, prompt assembly, and response quality between `/chat` (non-streaming) and `/chat/stream` (streaming) across 5 representative queries:

1. `"Hey Saki"`
2. `"What is FastAPI?"`
3. `"What is the latest Python version?"`
4. `"What is special about Kambadur Temple in Andhra Pradesh?"`
5. `"Write a Python function to reverse a string."`

**Inspection Criteria**:
- Parity of routing decision, model selection, memory retrieval, and evidence processing.
- Evaluation and memory persistence consistency between endpoints.
