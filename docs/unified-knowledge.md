# Saki AI — Unified Knowledge & RAG Subsystem Specification
**Sprint 13 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Unified Knowledge & RAG Subsystem  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Unified Knowledge Engine ([`UnifiedKnowledgeEngine`](file:///c:/Users/gurus/work/saki/backend/services/unified_knowledge.py#L60)) is a capability module within Saki's existing central orchestrator—**NOT a secondary RAG agent (`KnowledgeAgent`, `RAGAgent`, `RetrievalAgent`), second memory system, or separate vector database**.

All knowledge retrieval across memory, codebase files, GitHub state, and web evidence routes through a single central interface while preserving source trust and strict prompt injection defense.

```
                         SAKI CENTRAL BRAIN (SakiModelOrchestrator in chat.py)
                                       │
                                       ▼
                       UNIFIED KNOWLEDGE & RAG ENGINE
                     (backend/services/unified_knowledge.py)
                                       │
           ┌───────────────┬───────────┼───────────┬───────────────┐
           ▼               ▼           ▼           ▼               ▼
        MEMORY        DOCS/CODE     GITHUB     WEB_EVIDENCE   PERSONAL_CTX
       (Sprint 6)     (Sprint 9)  (Sprint 10)  (Sprint 3-5)    (Sprint 12)
           │               │           │           │               │
           └───────────────┴───────────┼───────────┴───────────────┘
                                       ▼
                     1. Provenance Tagging & Source Trust
                     2. Semantic & Keyword Hybrid Ranking
                     3. Deduplication & Context Minimization
                     4. Privacy Engine Secret Redaction (Sprint 2)
                     5. Conflict Detection & Prompt Injection Defense
                                       │
                                       ▼
                             RANKED KNOWLEDGE PACKAGE
                                       │
                                       ▼
                                  SAKI BRAIN
```

---

## 2. SOURCE TRUST & PROVENANCE LEVELS

Every retrieved candidate item retains explicit provenance and source trust weighting:
- `USER_MEMORY` & `CODE`: `TRUST_AUTHORITATIVE` (1.0)
- `LOCAL_DOCUMENT`: `TRUST_HIGH` (0.85)
- `GITHUB`: `TRUST_MEDIUM` (0.70)
- `WEB_SOURCE`: `TRUST_EXTERNAL` (0.50) + `is_untrusted_data = True`

---

## 3. PROMPT INJECTION DEFENSE & PRIVACY

- **Prompt Injection Defense**: [`UnifiedKnowledgeEngine.sanitize_prompt_injections()`](file:///c:/Users/gurus/work/saki/backend/services/unified_knowledge.py#L70) neutralizes adversarial instructions (`"Ignore previous instructions"`, `"override policy"`) found in external web text or issue descriptions by replacing them with `[REDACTED_PROMPT_INJECTION_ATTEMPT]`.
- **Outbound Privacy**: Outbound queries pass through Sprint 2 `PrivacyPolicyEngine` to redact API keys, passwords, and private user credentials.
