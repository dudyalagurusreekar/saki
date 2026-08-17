# Factual Grounding & Retrieval Verification Architecture

This plan aligns Saki's RAG and search workflows with the user's architectural guidelines. Gemini acts strictly as Saki's external information capability (retriever) rather than a conversational agent. Saki's local LLM remains the sole brain and conversational persona.

## User Review Required

> [!IMPORTANT]
> - **Model Bypass**: We will bypass live Ollama model calls during testing to maintain test suite speed.
> - **Relevance Check**: If search results do not contain key query terms (e.g. returning "Tadipatri" when looking for "Kambadur"), Saki rejects the evidence and states she doesn't know, preventing hallucinations.

---

## Proposed Changes

### Action Engine

#### [MODIFY] [action_engine.py](file:///c:/Users/gurus/work/saki/backend/services/action_engine.py)
- Detect explicit verification requests (e.g. `"verify"`, `"is this correct"`, `"confirm this"`) near the top of `decide_action`.
- Set `query_intent = "verification"` and `requires_world_access = True` to ensure verification queries run through the search pipeline.

---

### Gemini Search Provider

#### [MODIFY] [gemini_search.py](file:///c:/Users/gurus/work/saki/backend/services/gemini_search.py)
- Update the Gemini Google Search grounding payload to pass a structured task instruction prompt instead of raw queries. 
- Instruct Gemini to act purely as an information extractor (returning raw facts + source URLs) instead of writing conversational replies.

---

### Chat Route

#### [MODIFY] [chat.py](file:///c:/Users/gurus/work/saki/backend/routes/chat.py)
- Implement `check_evidence_relevance(query, evidence_items)` to strip filler words and verify if key terms are found in retrieved results.
- In `_execute_chat_pipeline`, check the relevance of retrieved evidence:
  - **Irrelevant/Empty**: Clear evidence list and inject a strict `[CRITICAL DIRECTIVE: Refuse to guess/speculate, say you don't know/couldn't retrieve info]` prompt instruction.
  - **Verification Mode**: Inject `[VERIFICATION DIRECTIVE: Perform deep source comparison, point out conflicts, cite domains]`.
  - **Normal Retrieval Mode**: Inject `[FACTUAL DIRECTIVE: Answer naturally as Saki using the facts directly without calling it verification]`.

---

## Verification Plan

### Automated Tests
We will run our complete backend test suite:
- `.\venv\Scripts\python -m pytest backend/tests/ -v`

### Manual Verification
We will run verification scripts simulating:
- Obscure query with matching results (should answer).
- Obscure query with irrelevant/mismatched results (should decline/refuse to guess).
- Explicit verification requests (should perform source comparison).
