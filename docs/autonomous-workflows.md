# Saki AI — Advanced Autonomous Workflows Subsystem Specification
**Sprint 19 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Advanced Autonomous Workflows Subsystem  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Autonomous Workflows Engine ([`AutonomousWorkflowEngine`](file:///c:/Users/gurus/work/saki/backend/services/autonomous_workflow.py#L75)) extends Sprint 11 Persistent Tasks to execute approved, multi-step objectives—**WITHOUT creating a secondary autonomous agent (`WorkflowAgent`, `AutonomousAgent`, `OrchestratorAgent`, `PlanningAgent`, `ExecutionAgent`), second planner, or second task engine**.

```
User Objective
      ↓
Saki Central Brain (SakiModelOrchestrator in chat.py)
      ↓
Plan Bounded Workflow & Validate Permissions (SakiWorkflow & WorkflowStep)
      ↓
Execute Approved Step (via S1 Action Engine, S9 Dev Capability, S10 Git Capability)
      ↓
Persist Step Checkpoint & Verify Idempotency (data/persistent_tasks.json)
      ↓
Verify Step Completion (Sprint 17 Truth Verification)
      ↓
Dynamic Replanning / Objective Drift Detection
      ↓
Next Step / Awaiting User Approval / Complete
      ↓
Report Verified Final Result
```

---

## 2. WORKFLOW STATES & BOUNDED EXECUTION LIMITS

- **Workflow States**: `PLANNED`, `READY`, `RUNNING`, `WAITING`, `AWAITING_USER`, `BLOCKED`, `FAILED`, `COMPLETED`, `CANCELLED`, `EXPIRED`.
- **Bounded Execution Limits**:
  - `MAX_STEPS`: 5 max per workflow
  - `MAX_ACTIONS`: 10 max per workflow
  - `MAX_PARALLEL_STEPS`: 1 (Strictly sequential step execution)
  - `CHILD_WORKFLOW_CREATION`: BLOCKED (Prevents recursive workflow explosions)

---

## 3. CHECKPOINTING, RECOVERY & SECURITY GUARDRAILS

- **Checkpointing & Idempotency**: Each step execution persists checkpoint status and an `idempotency_token` to prevent repeating completed side effects.
- **Application Restart Recovery**: [`AutonomousWorkflowEngine.recover_workflows()`](file:///c:/Users/gurus/work/saki/backend/services/autonomous_workflow.py#L160) restores pending workflows from step checkpoints on restart.
- **Permission Escalation Blockage**: Steps requiring elevated permissions (e.g. `ADMIN_CONFIRMATION` or Git pushes) transition to state `AWAITING_USER` when permissions are missing. Workflows **cannot** grant themselves permissions.
