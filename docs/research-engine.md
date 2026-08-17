# Saki AI — Bounded Autonomous Web Research Subsystem Specification
**Sprint 5 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Bounded Autonomous Research Planner  

---

## 1. RESEARCH SUBSYSTEM ARCHITECTURE

The Bounded Autonomous Web Research Subsystem coordinates multi-step research operations when Saki's Cognitive Action Engine detects `action == WEB_RESEARCH`:

```
                  [ User Question / ChatRequest ]
                                │
                                ▼
            [ Cognitive Action Engine (WEB_RESEARCH) ]
                                │
                                ▼
         [ ResearchPlanner (backend/services/research_planner.py) ]
         (Formulates ResearchPlan & initial ResearchBudget)
                                │
                                ▼
               ┌───────────────────────────────────┐
               │     BOUNDED RESEARCH LOOP         │
               │                                   │
               │  1. Check Hard Budget & Runtime   │
               │  2. Gap & Conflict Analysis       │
               │  3. Query Generation/Diversification│
               │  4. Privacy Gate Check            │
               │  5. World Access Search/Fetch     │
               │  6. Evidence Engine Evaluation    │
               │  7. Check Stop Conditions         │
               └───────────────────────────────────┘
                                │
                                ▼
                      [ ResearchResult ]
                                │
                                ▼
           [ Grounded Prompt Synthesizer + XML Sandbox ]
           (<external_web_content> with [Source 1..N] Citations)
                                │
                                ▼
                    [ Local LLMs (Phi-3/Qwen-3) ]
```

---

## 2. DATA MODELS & SAFEGUARDS

### ResearchBudget
Executable Python limits that CANNOT be overridden by model outputs:
- `max_searches`: Default 3 (1 for QUICK, 5 for DEEP)
- `max_fetches`: Default 2
- `max_depth`: Default 3
- `max_runtime`: Default 15.0 seconds
- `max_total_results`: Default 15 items
- `max_total_bytes`: Default 1,000,000 bytes (1MB)

### ResearchPlan
- `research_id`: Unique research ID (`res-123456`)
- `original_question`: User's original request
- `objective`: Research goal
- `initial_queries`: Initial search queries
- `budget`: `ResearchBudget` instance
- `stop_conditions`: List of stopping criteria

### ResearchState
- `completed_steps`: Completed `ResearchStep` items
- `raw_results_collected`: Cumulative web results
- `evidence_package`: Evaluated `EvidencePackage` (Sprint 4)
- `searches_count`, `fetches_count`, `depth_count`: Hard counter tracking
- `stop_reason`: Reason for loop termination

---

## 3. STOPPING CONDITIONS

The research loop terminates immediately when ANY of the following conditions evaluate to true:
1. **`EVIDENCE_SUFFICIENT`**: Evidence package contains sufficient verified facts with domain diversity.
2. **`BUDGET_EXHAUSTED`**: Search, fetch, or runtime limit reached.
3. **`MAX_DEPTH_REACHED`**: Maximum research generation depth reached.
4. **`NO_NEW_INFORMATION`**: Successive search returned zero new unique items.
5. **`PRIVACY_BLOCKED`**: Outbound query was blocked by local Privacy Boundary.
6. **`CONFLICT_UNRESOLVABLE`**: Contradictory evidence could not be resolved within budget limits.

---

## 4. PROMPT INJECTION & UNTRUSTED DATA SAFETY

External web content cannot alter research policy or bypass privacy rules:
- Loop bounds are hardcoded Python `while` conditions.
- Generated queries pass through `PrivacyPolicyEngine.evaluate_request()`.
- Retrieved web text is isolated inside `<external_web_content>` XML tags and treated as reference data only.

---

## 5. INTEGRATION WITH CHAT PIPELINE

In `backend/routes/chat.py`:
1. When `action_decision.action == "WEB_RESEARCH"`, `ResearchPlanner.execute_research()` executes.
2. The synthesized `ResearchResult` grounded prompt block is appended to LLM prompt input.
3. Telemetry metadata is returned in `ChatResponse.research_result`.
