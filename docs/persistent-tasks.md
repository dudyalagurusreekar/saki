# Saki AI — Integrated Persistent Tasks, Proactive Monitoring & Continuation Specification
**Sprint 11 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Integrated Persistent Tasks & Proactive Monitoring Capability  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Integrated Persistent Task Capability (`PersistentTaskCapability`) is a capability module within Saki's existing central orchestrator—**NOT a secondary scheduler-brain, background monitoring agent, or separate orchestrator**.

The scheduler is strictly an execution mechanism that wakes Saki's central brain to re-evaluate task state. It **NEVER independently decides what Saki should think, remember, modify, or do**.

```
TEMPORARY CONVERSATION
        ↓
SAKI CENTRAL BRAIN (SakiModelOrchestrator in chat.py)
        ↓
ACTION ENGINE (SCHEDULE_TASK, LIST_TASKS, PAUSE_TASK, CANCEL_TASK)
        ↓
PERSISTENT TASK CAPABILITY (backend/services/task_capability.py)
        ├── 1. SakiTask Model (Objective, schedule_type, capability_scope, checkpoint, history)
        ├── 2. Task State Machine (CREATED -> PLANNED -> READY -> RUNNING -> WAITING -> COMPLETED)
        ├── 3. TaskStorageEngine (Persists to data/persistent_tasks.json & recover_tasks())
        ├── 4. TaskSchedulerEngine (Wakes Saki central brain for condition evaluation)
        ├── 5. Least Privilege Scope (WEB_READ, GITHUB_READ, NOTIFICATION capability isolation)
        └── 6. Task Budget Guard (MAX_TASK_EXECUTIONS = 10, MAX_TASK_FAILURES = 3)
        ↓
LOCAL LLM ANSWER GENERATION & TELEMETRY
```

---

## 2. TASK STATE MACHINE

```
CREATED ──► PLANNED ──► READY ──► RUNNING ──► WAITING ──► COMPLETED
                             │           │
                             ▼           ▼
                           PAUSED     FAILED / EXPIRED / CANCELLED
```

---

## 3. RESTART RECOVERY & PERSISTENCE

- **Task Storage**: Task definitions, checkpoints, and execution histories are stored in `data/persistent_tasks.json`.
- **Restart Recovery**: [`TaskStorageEngine.recover_tasks()`](file:///c:/Users/gurus/work/saki/backend/services/task_capability.py#L118) executes on server startup. Any task interrupted in the `RUNNING` state during a system restart transitions safely to `WAITING` without duplicating external side effects.

---

## 4. LEAST PRIVILEGE CAPABILITY SCOPING

Tasks are granted only the minimum capability scope required for their specific objective:
- `WEB_READ`: Read public web search results
- `GITHUB_READ`: Inspect GitHub issues and PR status
- `BROWSER_READ`: DOM page state inspection
- `NOTIFICATION`: Send user status alerts

Unassigned capabilities (e.g. `COMPUTER_WRITE`, `GIT_PUSH`) remain strictly forbidden.
