# Web Reliability Hardening Architecture Plan

This plan outlines the design and implementation details for the **Web Reliability Hardening Sprint** (Phase 3 through Phase 11).

## User Review Required

> [!IMPORTANT]
> - **Provider Transparency**: Failures or fallbacks from Gemini will be flagged explicitly with metadata (`status="FAILED"` or `"FALLBACK"`, `fallback_from="gemini"`). Fallback data is never labeled as Gemini.
> - **Three-State Relevance Gate**: We will run candidates through `phi3:latest` (or local fallback) classifying them into `RELEVANT`, `IRRELEVANT`, or `UNCERTAIN`:
>   - `RELEVANT` -> Continue.
>   - `IRRELEVANT` -> Reject.
>   - `UNCERTAIN` -> Fall back to deterministic entity check. If relevance is still not established, FAIL CLOSED (Reject).
> - **Factual Grounding & Verification States**:
>   - State machine: `RETRIEVED` -> `RELEVANT` -> `SUPPORTED` -> `VERIFIED` (only after multi-source comparison, never automatically).
> - **Failsafe Refusal Directives**: If all search results are filtered out as irrelevant, Saki will receive a strict directive to refuse guessing and respond with a natural "I don't know".

---

## Proposed Changes

### Gemini Search Provider

#### [MODIFY] [gemini_search.py](file:///c:/Users/gurus/work/saki/backend/services/gemini_search.py)
- Update `GeminiSearchProvider.search` to return metadata detailing success/failure status and fallback provenance (`provider_status`, `fallback_from`, `error_detail`).
- Update `search_grounded` to expose these status variables transparently.

---

### World Access Manager

#### [MODIFY] [world_access_manager.py](file:///c:/Users/gurus/work/saki/backend/services/world_access_manager.py)
- Propagate status and fallback flags (`provider_status`, `fallback_from`, `error_detail`) from the provider to the `EvidenceItem.provenance` block in `normalize_search_results`.
- Pass `is_verification_mode` parameter to the `EvidenceIntelligenceEngine.process_and_synthesize` synthesizer.

---

### Evidence Engine

#### [MODIFY] [evidence_engine.py](file:///c:/Users/gurus/work/saki/backend/services/evidence_engine.py)
- Add `process_state: str = "RETRIEVED"` to `EvidenceItem`.
- Update `ClaimModel.support_status` to support `CLAIM_SUPPORT` state.
- Implement `RelevanceGate` class supporting:
  - Batch local AI relevance checking using `phi3:latest`, returning `["RELEVANT", "IRRELEVANT", "UNCERTAIN"]`.
  - Deterministic entity/location keyword matching for `UNCERTAIN` results and when local AI is offline.
  - Fail-closed reject rules: any result that remains `UNCERTAIN` is rejected.
- Update `EvidenceIntelligenceEngine.process_and_synthesize` to:
  - Filter raw items using `RelevanceGate`.
  - Mark matching candidates as `process_state="RELEVANT"`.
  - Only extract claims and set status as `SUPPORTED` for relevant items.
  - Run multi-source verification checking in verification mode to optionally elevate claims to `VERIFIED` or flag them as `CONFLICT`.
- Update `format_grounded_prompt_block` to only present relevant sources in the final XML output.

---

### Chat Routes

#### [MODIFY] [chat.py](file:///c:/Users/gurus/work/saki/backend/routes/chat.py)
- Clean up redundant code and integrate the new `EvidencePackage.evidence_status` checks:
  - If the package has `EVIDENCE_STATUS_INSUFFICIENT` (e.g. all candidates were rejected by the Relevance Gate), clear the evidence and inject the strict "I don't know" directive.
  - If verification was requested, inject verification mode directives.
  - If normal search was run, inject standard factual grounding directives.

---

## Verification Plan

### Automated Regression Tests
We will add 6 new target regression tests in `backend/tests/test_gemini_search.py` verifying:
1. **Kambadur Temple Case**: Returns "I don't know" when search results are irrelevant.
2. **Vijayawada Places Case**: Filters out unrelated location candidates (e.g., Yelahanka Fort).
3. **Normal Knowledge Query**: Direct LLM response (no search triggered).
4. **Current Information Query**: Web search triggered.
5. **Explicit Verification Query**: Multi-source conflict comparison mode activated.
6. **Impossible/Unknown Entities**: Safe refusal ("I don't know").

We will execute the complete test suite:
- `.\venv\Scripts\python -m pytest backend/tests/ -v`
