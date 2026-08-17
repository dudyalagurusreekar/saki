# Walkthrough - Web Reliability Hardening

We have successfully implemented and stabilized the **Web Reliability Hardening Sprint** (Phase 3 through Phase 11), ensuring transparent search provider status tracking, strict relevance gating, a clean evidence state machine, and robust failsafe paths.

## Key Changes Made

### 1. Provider Transparency & Fallback Attribution
- Modified `GeminiSearchProvider` to explicitly track query grounding execution statuses:
  - Successful queries are marked with `provider_status = "SUCCESS"`.
  - Intended fallbacks are tracked with `provider_status = "FALLBACK"` and `fallback_from = "gemini"`.
  - Internal exceptions or empty grounding results are explicitly documented in `error_detail` (e.g. `DISABLED`, `EMPTY_GROUNDING`, `HTTP_500`).
- Propagated these variables in `EvidenceItem.provenance` to ensure complete logging transparency.

### 2. Relevance Gate
- Implemented `RelevanceGate` supporting a strict 3-state evaluation pipeline: `RELEVANT`, `IRRELEVANT`, `UNCERTAIN`.
- Integrated a fast batch semantic evaluator (local AI via `phi3:latest` when available) to map query entities and relationships.
- Designed a deterministic regex/entity-matching filter to evaluate `UNCERTAIN` entries or when local AI is offline.
- Ensured **fail-closed** behavior: if a candidate query relation cannot be established as relevant, it is rejected.

### 3. Factual Grounding & Verification State Machine
- Refined the lifecycle transitions: `RETRIEVED` -> `RELEVANT` -> `SUPPORTED` -> `VERIFIED` (under verification workflows, never automatically).
- In verification mode, the engine evaluates contradicting claims using the conflict detector. Consistent claims are flagged as `VERIFIED` and contradictory claims are flagged as `CONFLICT`.
- Only `RELEVANT` candidates contribute to claims and final XML prompts; all others are rejected to prevent hallucination.

### 4. Failsafe "I Don't Know" Path
- Modified the chat pipeline route so that if the relevance gate rejects all candidates (package status is `INSUFFICIENT`), Saki drops the empty evidence and receives a strict directive to refuse guessing and explain she has no verified records.

---

## Verification & Tests

We restructured and successfully ran 197 tests, introducing target integration coverage:
- **`test_gemini_search.py`**: Success, HTTP failure, fallback provenance, and empty grounding scenarios.
- **`test_relevance_gate.py`**: Kambadur temple matches, Vijayawada filters (rejects Yelahanka Fort), unrelated entity blocks, and fail-closed rejections.
- **`test_web_routing.py`**: Normal stable queries (bypasses search) vs current/obscure queries (triggers search).
- **`test_verification.py`**: Verification intents, multi-source claim conflicts, and verified status checks.

### Test Log Results
```
backend/tests/test_gemini_search.py::test_provider_success PASSED
backend/tests/test_gemini_search.py::test_provider_failure PASSED
backend/tests/test_gemini_search.py::test_fallback_provenance PASSED
backend/tests/test_gemini_search.py::test_empty_or_malformed_gemini_response PASSED
backend/tests/test_relevance_gate.py::test_kambadur_temple_relevance_matching PASSED
backend/tests/test_relevance_gate.py::test_vijayawada_places_filtering PASSED
backend/tests/test_relevance_gate.py::test_unrelated_entity_rejection PASSED
backend/tests/test_relevance_gate.py::test_uncertain_results_fail_closed PASSED
backend/tests/test_web_routing.py::test_normal_knowledge_routing PASSED
backend/tests/test_web_routing.py::test_current_information_routing PASSED
backend/tests/test_web_routing.py::test_obscure_entity_routing PASSED
backend/tests/test_verification.py::test_explicit_verification_request_intent PASSED
backend/tests/test_verification.py::test_multi_source_conflict_comparison PASSED
backend/tests/test_verification.py::test_verified_vs_unsupported_claims PASSED

=============== 197 passed, 1105 warnings in 102.29s (0:01:42) ================
```
