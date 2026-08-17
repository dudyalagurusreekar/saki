# Saki AI — Knowledge Fusion & Cross-Source Reasoning Specification
**Sprint 14 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Knowledge Fusion & Cross-Source Reasoning Subsystem  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Knowledge Fusion Engine ([`KnowledgeFusionEngine`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_fusion.py#L55)) is a capability module built on top of Sprint 13 Unified Knowledge Retrieval—**NOT a secondary reasoning agent (`FusionAgent`, `KnowledgeAgent`, `ReasoningAgent`), second RAG, or second evidence engine**.

The subsystem transforms retrieved candidate items into structured claims, evaluates contextual authority, detects cross-source contradictions, and presents a grounded evidence package to Saki's central brain for reasoning.

```
Saki Brain (SakiModelOrchestrator in chat.py)
    ↓
S13 Unified Retrieval (UnifiedKnowledgeEngine)
    ↓
Candidate Evidence
    ↓
Knowledge Fusion Engine (backend/services/knowledge_fusion.py)
    ├── 1. Source Normalization & Mirror Deduplication
    ├── 2. Claim Extraction & Multi-Source Claim Grouping
    ├── 3. Contextual Authority (Code > Memory, Official Docs > Random Web)
    ├── 4. Conflict Detection (Repository v3 vs Docs v2 -> SourceConflict)
    ├── 5. Evidence Support Scoring (SUPPORTED, CONFLICTING, UNSUPPORTED)
    └── 6. Prompt Injection Defense (Retrieved text remains untrusted DATA)
    ↓
Privacy Policy Engine (Sprint 2 Outbound Boundary)
    ↓
Ranked & Fused Evidence Context (ChatResponse.knowledge_fusion)
    ↓
Saki Brain (Reasoning & Grounded Answer Generation with Provenance)
```

---

## 2. CONTEXTUAL AUTHORITY & FRESHNESS REASONING

- **Contextual Authority**: Saki applies context-aware authority weights:
  - Current codebase implementation > Old memory facts
  - Official documentation > Random web snippets
  - Explicit current user statements > Weak model inferences
- **Freshness Evaluation**: Information is classified into `FRESH_CURRENT`, `FRESH_RECENT`, `FRESH_STALE`, and `FRESH_UNKNOWN`. Time-sensitive queries prioritize `FRESH_CURRENT` codebase and Git state.

---

## 3. CONFLICT DETECTION & PROMPT INJECTION DEFENSE

- **Conflict Detection**: When candidates present direct contradictions (e.g. Repository says v1 vs Documentation says v2), [`KnowledgeFusionEngine.fuse_knowledge()`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_fusion.py#L65) creates an explicit [`SourceConflict`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_fusion.py#L42) object without manufacturing false certainty.
- **Prompt Injection Defense**: Retrieved evidence remains untrusted DATA. Malicious prompt injection strings (`"Ignore previous instructions"`) cannot modify system policy or execute unauthorized commands.
