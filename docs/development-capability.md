# Saki AI — Integrated Development & Code Engineering Specification
**Sprint 9 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Integrated Development & Code Engineering Capability  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Integrated Development Capability (`DevelopmentCapability`) is a capability module within Saki's existing central orchestrator—**NOT a secondary brain, autonomous coding agent, or separate orchestrator**.

All development operations reuse Saki's core infrastructure:
- **Central Decision Maker**: `SakiModelOrchestrator` ([`backend/routes/chat.py`](file:///c:/Users/gurus/work/saki/backend/routes/chat.py#L350))
- **Action Engine**: Sprint 1 Action Decision (`action == "CODING"`)
- **Privacy Engine**: Sprint 2 secret redaction & outbound validation
- **World Access**: Sprint 3 web search & documentation fetch
- **Evidence Engine**: Sprint 4 XML prompt isolation (`<external_web_content>`)
- **Research Planner**: Sprint 5 bounded web research
- **Memory Subsystem**: Sprint 6 project decision storage (`TYPE_PROJECT_MEMORY`)
- **Browser Controller**: Sprint 7 read-only web page DOM observation
- **Computer Controller**: Sprint 8 workspace sandbox & command risk policy

```
USER REQUEST
     ↓
SAKI CENTRAL BRAIN (SakiModelOrchestrator)
     ↓
ACTION ENGINE (Action = "CODING")
     ↓
DEVELOPMENT CAPABILITY (backend/services/development_capability.py)
     ├── 1. RepositoryScanner (Discovers source/test dirs, manifests, ignores .git/venv)
     ├── 2. CodeSearchEngine & SecretRedactor (Line-numbered snippets, masks secrets)
     ├── 3. DevelopmentPlan & ChangeProposal Generation (Unified diff preview)
     ├── 4. Controlled Workspace Modification (Path containment, rollback checkpoint)
     ├── 5. Targeted Test Execution (S8-sandboxed Pytest execution)
     └── 6. Bounded Debug Loop (MAX_REPAIR_ITERATIONS = 3)
     ↓
LOCAL LLM ANSWER GENERATION & TELEMETRY
```

---

## 2. WORKFLOW STAGES

1. **`UNDERSTAND`**: `RepositoryScanner` inspects workspace directories, source files, and test manifests.
2. **`PLAN`**: `CodeSearchEngine` finds relevant symbols and constructs a `DevelopmentPlan`.
3. **`PERMISSION`**: Evaluates risk level (`READ_ONLY`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
4. **`MODIFY`**: Performs safe file writes after saving a rollback checkpoint.
5. **`TEST`**: Executes targeted pytest runs via Sprint 8 `ComputerController`.
6. **`VERIFY`**: Validates exit codes and test pass status.
7. **`REPORT`**: Formats completion summary and exposes `development_task` telemetry.

---

## 3. CHANGE PROPOSALS & RISK MATRIX

| Risk Level | Target Operations | Permission / Policy |
|---|---|---|
| `READ_ONLY` | Code search, symbol inspection, repository scanning | Authorized automatically |
| `LOW` | Modifying test files, documentation updates | Authorized within active workspace |
| `MEDIUM` | Modifying backend routes, core services | Authorized within active workspace |
| `HIGH` | Modifying dependency manifests (`requirements.txt`, `pyproject.toml`) | Requires elevated risk classification |
| `CRITICAL` | Security configuration, authentication logic | Requires explicit user confirmation |

---

## 4. BUDGET LIMITS & SAFETY SAFEGUARDS

- **`MAX_FILES_PER_TASK`**: 5 files max per task.
- **`MAX_LINES_CHANGED`**: 500 lines max per task.
- **`MAX_REPAIR_ITERATIONS`**: 3 debug iterations max before halting.
- **Atomic Rollback**: `DevelopmentCapability.rollback_file()` restores original baseline content if needed.
