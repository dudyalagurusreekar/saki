# Grounding & Verification Architecture Walkthrough

We have successfully implemented Saki's new factual grounding and verification architecture. Gemini now functions strictly as Saki's external information capability (retriever), with Saki's local LLM serving as the sole cognitive brain.

## Changes Made

### 1. Verification Intent Detection
- File: [action_engine.py](file:///c:/Users/gurus/work/saki/backend/services/action_engine.py#L207-L230)
- In `decide_action`, we added an explicit check for verification phrases (e.g., `"verify"`, `"confirm"`, `"is this true"`, `"is this correct"`).
- Requests containing these trigger an immediate `ACTION_WEB_SEARCH` routing decision with `query_intent = "verification"`.

### 2. Task-Oriented Grounding Prompts
- File: [gemini_search.py](file:///c:/Users/gurus/work/saki/backend/services/gemini_search.py#L41-L60)
- Instead of raw queries, Saki now queries the Gemini grounding engine using a highly structured system instruction task.
- Gemini is instructed to act purely as an information extractor (returning raw facts + source URLs) instead of writing conversational replies.

### 3. Relevance Filtering & Anti-Hallucination Guard
- File: [chat.py](file:///c:/Users/gurus/work/saki/backend/routes/chat.py#L335-L389)
- We implemented `check_evidence_relevance(query, evidence_items)` to clean search filler and verify if the primary entity/search keywords exist inside the retrieved title or snippets.
- In `_execute_chat_pipeline` [chat.py:L473-L513](file:///c:/Users/gurus/work/saki/backend/routes/chat.py#L473-L513):
  - **If Irrelevant/Empty**: Search details are rejected. We inject a strict directive forcing Saki to refuse speculation and state clearly that she doesn't know / couldn't retrieve info.
  - **If Verification Mode**: We append a verification directive forcing Saki to compare sources, point out conflicts, and cite domains.
  - **If Normal Mode**: We append a factual directive instructing Saki to use retrieved facts directly and conversationally without detailing the search process unless asked.

---

## Verification Results

### Automated Tests
- Command: `.\venv\Scripts\python -m pytest backend/tests/ -v`
- Result: **191 tests passed successfully (0 failures)**.
