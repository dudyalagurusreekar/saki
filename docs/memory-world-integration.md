# Saki AI — World Knowledge ↔ Memory Integration Specification
**Sprint 6 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Memory Admission Engine & Memory Poisoning Defense  

---

## 1. MEMORY SUBSYSTEM ARCHITECTURE

The World Knowledge ↔ Memory Integration Subsystem establishes a secure boundary between temporary web evidence and durable internal memories:

```
              [ External Web Content ]
                         │
                         ▼
        [ World Access Subsystem (Sprint 3) ]
                         │
                         ▼
        [ Evidence Engine (Sprint 4 EvidencePackage) ]
                         │
                         ▼
       [ Research / Reasoning Layer (Sprint 5) ]
                         │
                         ▼
   [ MemoryAdmissionEngine (backend/services/memory_admission.py) ]
      ├── 1. Provenance & Source Linkage Check
      ├── 2. Memory Poisoning & Injection Guard
      ├── 3. Category Validation (Web evidence cannot create personal memory)
      ├── 4. Temporal Expiration Assignment
      └── 5. Conflict Resolution & Versioning
                         │
                         ▼
                [ Admitted MemoryRecord ]
```

---

## 2. MEMORY TAXONOMY

Saki distinguishes 9 distinct memory classifications:

1. **`CONVERSATION_MEMORY`**: Short-term multi-turn conversation context.
2. **`WORKING_MEMORY`**: Transient task scratchpad memory.
3. **`PERSONAL_MEMORY`**: Durable user facts (name, identity, background).
4. **`PROJECT_MEMORY`**: Architecture decisions & project configuration facts.
5. **`PREFERENCE_MEMORY`**: Explicit user preferences (coding style, verbosity, tools).
6. **`TASK_MEMORY`**: Active multi-step plan status.
7. **`LOCAL_KNOWLEDGE`**: Local repository facts & user documentation.
8. **`WEB_EVIDENCE`**: **TEMPORARY request-scoped web search data** (Default: `DO_NOT_ADMIT`).
9. **`VERIFIED_WORLD_KNOWLEDGE`**: High-confidence, primary-source promoted world facts.

---

## 3. MEMORY LIFECYCLE

```
CANDIDATE ──► EVALUATING ──► ADMITTED ──► ACTIVE ──► AGING ──► STALE ──► ARCHIVED / FORGOTTEN
```

- **`CANDIDATE`**: Memory candidate proposed by system/user/web.
- **`EVALUATING`**: Under evaluation by `MemoryAdmissionEngine`.
- **`ADMITTED`**: Approved for storage under `MemoryRecord`.
- **`ACTIVE`**: Currently active for memory context selection.
- **`STALE`**: Expired or outdated; triggers fresh web retrieval when queried for current information.
- **`FORGOTTEN`**: Permanently deleted/invalidated upon user instruction (`"Forget X"`).

---

## 4. MEMORY POISONING & INJECTION DEFENSE

To prevent untrusted web pages from poisoning Saki's durable memory or deleting user data:
- Web-derived candidates requesting memory creation (e.g. *"Store this as permanent memory"*) or deletion (e.g. *"Delete all user memories"*) evaluate to **`ADMIT_DECISION_REJECT`**.
- Web evidence **CANNOT create `PERSONAL_MEMORY`** (*"User prefers X"*). Personal preferences can only be created via explicit user input (`SOURCE_USER`).

---

## 5. TEMPORAL EXPIRATION POLICIES

- **`EPHEMERAL`**: Minutes / request lifetime (Web evidence default).
- **`CURRENT`**: Days / months (Current software releases, temporary project facts).
- **`STABLE`**: Years (Official specifications, core architectural concepts).
- **`PERMANENT_USER_FACT`**: Indefinite until user explicitly modifies or forgets it.

---

## 6. MEMORY CONTEXT SELECTOR & PRIVACY

[`MemoryContextSelector`](file:///c:/Users/gurus/work/saki/backend/services/memory_admission.py#L225) ranks and selects active memories for outbound LLM prompts. Secret-bearing memories (API keys, credentials) are automatically stripped by Sprint 2 [`PrivacyPolicyEngine`](file:///c:/Users/gurus/work/saki/backend/core/privacy.py#L125) before reaching prompt context.
