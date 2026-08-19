# SPRINT 1 — SAKI WEB EXECUTION FLOW ANALYSIS

**Repository**: `https://github.com/dudyalagurusreekar/saki`  
**Branch**: `p1`  
**Sprint**: Sprint 1 — Unify & Activate Saki Web Intelligence

---

## 1. Trace of Current (Before) Web Execution Paths

Prior to Sprint 1, a single incoming user query to `/chat` or `/chat/stream` could trigger up to **4 independent, redundant web search pipelines** during a single request lifecycle:

```
[USER QUERY]
     │
     ├── 1. GATED ACTION DISPATCH (chat.py L405-L424)
     │      └── if action.requires_world_access:
     │            └── WorldAccessManager.execute_action_package()
     │                  ├── PrivacyPolicyEngine.evaluate_request()
     │                  ├── GeminiSearchProvider.search() [Search Pass 1]
     │                  └── EvidenceIntelligenceEngine.process_and_synthesize()
     │
     ├── 2. UNIFIED RAG SUBSYSTEM (chat.py L516 -> unified_knowledge.py L156)
     │      └── if keyword in ["search", "web", "latest", "doc", "fastapi", "release", "current", "2026"]:
     │            └── UnifiedKnowledgeEngine.retrieve_knowledge()
     │                  └── GeminiSearchProvider.search() [Search Pass 2: REDUNDANT]
     │
     ├── 3. WEB INTELLIGENCE CAPABILITY (chat.py L522 -> web_intelligence.py L161)
     │      └── if keyword in ["search", "web", "latest", "doc", "fastapi"]:
     │            └── WebIntelligenceCapability.execute_web_intelligence()
     │                  ├── WebIntelligenceCapability.refine_queries() -> generates 2-3 queries
     │                  └── for q in refined_queries:
     │                        └── GeminiSearchProvider.search() [Search Passes 3, 4, 5: REDUNDANT]
     │
     └── 4. POST-GENERATION HELPLESS FALLBACK (chat.py L609 & L642)
            └── if is_helpless_response(model_output):
                  └── safe_search(user_input)
                        ├── expand_query()
                        └── multi_search() -> DuckDuckGo HTML Search [Search Pass 6: SILENT FALLBACK]
```

### Critical Flaws in the "Before" Architecture:
1. **Redundant Search Explosion**: A query like `"What is the latest FastAPI version?"` executed `WorldAccessManager` (Pass 1), `UnifiedKnowledgeEngine` (Pass 2), and `WebIntelligenceCapability` (Passes 3–5), issuing up to 5 external search calls for a single user turn.
2. **Silent Un-grounded Fallback**: If the model output triggered `is_helpless_response()`, `safe_search` secretly invoked DuckDuckGo and re-queried Qwen3, masking the true provider status.
3. **Activation Gaps & Date Misinterpretation**: `ActionEngine` treated `2026` as future information, failed to activate web search for local recommendations (e.g. `"special food in Vijayawada"`), and lacked date awareness for the current operating year (August 2026).

---

## 2. Unified (After) Web Execution Architecture

Sprint 1 unifies all web search, fetching, grounding, and synthesis under **ONE Authoritative Web Intelligence Controller** (`WebIntelligenceController`):

```
                       [USER QUERY]
                            │
                            ▼
              [ACTION DECISION ENGINE]
          (ActionEngine: 2026 Date Aware,
        Local/Recommendation Intent Detection)
                            │
                            ▼
              [WEB ACCESS REQUIRED?]
              ├── NO  ──> [LOCAL REASONING / CODING / MEMORY]
              │
              └── YES ──> [ONE WEB INTELLIGENCE CONTROLLER]
                               │
                               ├── 1. Privacy Gate & Query Sanitization
                               │      (PrivacyPolicyEngine)
                               │
                               ├── 2. Single Web Execution
                               │      (GeminiSearchProvider / WebFetcher)
                               │
                               ├── 3. Evidence Synthesis & Security
                               │      (EvidenceIntelligenceEngine)
                               │
                               └── 4. Structured Package Output
                                      ├── Structured EvidenceItems
                                      ├── Grounded XML Block (<external_web_content>)
                                      └── Web Telemetry (Zero Duplicates)
                                            │
                                            ▼
                               [CONTEXT COMPOSITION & MAIN CHAT]
                               ├── Injects Grounded XML into Prompt
                               ├── Shares Evidence with RAG/WebIntel (No Extra Searches)
                               │
                               ▼
                        [FINAL LLM INFERENCE]
                         (Strict Refusal if Insufficient)
```

---

## 3. Web Execution Responsibility Matrix

| Subsystem | Before Sprint 1 | After Sprint 1 (Unified) |
| :--- | :--- | :--- |
| **`ActionEngine`** | Static keywords; missed 2026 & local queries | Centralized intent detection, 2026 current year awareness, local/recommendation triggers |
| **`WebIntelligenceController`** | Non-existent (split across 3 classes) | **ONE authoritative entry point** for all external web grounding & fetching |
| **`GeminiSearchProvider`** | Called up to 5 times per request | Called **once** by the authoritative controller per search turn |
| **`UnifiedKnowledgeEngine`** | Executed its own `GeminiSearchProvider.search()` | Consumes evidence directly from the pipeline context |
| **`WebIntelligenceCapability`** | Executed 2–3 independent Gemini searches | Telemetry adapter consuming controller package |
| **`safe_search` Fallback** | Silent fallback to DuckDuckGo on "helpless" responses | **Removed**; fail-closed transparency enforced |
