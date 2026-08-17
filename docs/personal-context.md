# Saki AI — Integrated Personal Context & Proactive Assistance Specification
**Sprint 12 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Integrated Personal Context & Proactive Assistance Capability  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Integrated Personal Context Capability (`PersonalContextEngine`) is a capability module within Saki's existing central orchestrator—**NOT a secondary agent (`PersonalAgent`, `ContextAgent`, `ProactiveAgent`), second memory system, or surveillance system**.

Personal Context is **NOT surveillance**. Saki stores only what the user explicitly shared, authorized, or what was explicitly derived from approved Saki activities.

```
PERSONAL CONTEXT (USER_EXPLICIT / AUTHORIZED / SAKI ACTIVITY)
                         │
                         ▼
                   SAKI CENTRAL BRAIN
                         │
                         ▼
           CONTEXT RELEVANCE & SELECTION
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
    MEMORY          TASK STATE        CURRENT CHAT
  (Sprint 6)        (Sprint 11)       (Sprint 1)
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
           [ PersonalContextEngine ]
             ├── 1. Context Classification (IDENTITY, PREFERENCE, GOAL, PROJECT, TEMPORARY)
             ├── 2. Provenance & Confidence (USER_EXPLICIT=HIGH vs DERIVED=LOW)
             ├── 3. Minimal Context Budgeting (MAX_CONTEXT_ITEMS = 5)
             ├── 4. Conflict Resolution (Old facts -> SUPERSEDED, User Forget -> REVOKED)
             ├── 5. AttentionPolicy (SHOULD_NOTIFY, SHOULD_WAIT, SHOULD_ASK, SHOULD_IGNORE)
             └── 6. Memory Poisoning Guard (External web content CANNOT create personal facts)
                         │
                         ▼
             [ PrivacyPolicyEngine ] (Sprint 2 Outbound Secret Boundary)
                         │
                         ▼
             [ Saki Reasoning & Action Execution ]
```

---

## 2. CONTEXT CATEGORIES & PROVENANCE

Saki classifies context into 9 distinct categories:
- `IDENTITY_CONTEXT`: Explicit user identity facts
- `PREFERENCE_CONTEXT`: Coding and response style preferences
- `GOAL_CONTEXT`: Active short-term and long-term goals
- `PROJECT_CONTEXT`: Current project architecture facts
- `TASK_CONTEXT`: Active task status references
- `ROUTINE_CONTEXT`: User-approved interaction patterns
- `COMMITMENT_CONTEXT`: Deadlines and commitments
- `RELATIONSHIP_CONTEXT`: Explicitly shared relationship data
- `TEMPORARY_CONTEXT`: Expiring session-specific context

### Provenance & Confidence Rules
- `USER_EXPLICIT`: Directly stated by user -> `CONFIDENCE_HIGH`
- `DERIVED`: Inferred from activity -> `CONFIDENCE_LOW` (Cannot become permanent memory automatically)

---

## 3. CONFLICT RESOLUTION & USER FORGET

- **Conflict Resolution**: When new user statements contradict existing facts, old items transition to `SUPERSEDED` and new items become `ACTIVE`.
- **User-Controlled Forget**: When user requests *"Forget X"*, matching context items transition immediately to `REVOKED` and are excluded from retrieval.

---

## 4. PROACTIVE ASSISTANCE & ATTENTION POLICY

`AttentionPolicy` determines proactive behavior without intrusive nagging:
- `SHOULD_NOTIFY`: Send status alert for high-importance events
- `SHOULD_WAIT`: Defer notification during quiet hours or normal-priority events
- `SHOULD_ASK`: Prompt user for confirmation
- `SHOULD_IGNORE`: Suppress notification when proactive level is `OFF`
