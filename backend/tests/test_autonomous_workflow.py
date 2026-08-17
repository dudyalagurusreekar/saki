import pytest
from backend.services.autonomous_workflow import (
    AutonomousWorkflowEngine,
    SakiWorkflow,
    WorkflowStep,
    STATE_PLANNED,
    STATE_COMPLETED,
    STATE_AWAITING_USER,
    MAX_STEPS
)


# -------------------------
# WORKFLOW CREATION & EXECUTION TESTS
# -------------------------
def test_create_and_execute_bounded_workflow():
    wf = AutonomousWorkflowEngine.create_workflow("Prepare a fix for issue #42 and verify diff")
    
    assert isinstance(wf, SakiWorkflow)
    assert wf.status == STATE_PLANNED
    assert len(wf.steps) <= MAX_STEPS

    telemetry = AutonomousWorkflowEngine.execute_workflow(wf.workflow_id)
    assert telemetry.execution_status == "COMPLETED"
    assert telemetry.active_workflow.status == STATE_COMPLETED
    assert len(telemetry.active_workflow.checkpoint_data) == len(wf.steps)


# -------------------------
# PERMISSION ESCALATION GUARDRAIL TEST
# -------------------------
def test_permission_escalation_guardrail():
    wf = AutonomousWorkflowEngine.create_workflow("Administrative System Update")
    # Add step requiring admin confirmation
    wf.steps.append(WorkflowStep(
        step_id="step_admin",
        objective="Execute administrative system push",
        capability="GIT",
        permission_requirement="ADMIN_CONFIRMATION"
    ))
    
    telemetry = AutonomousWorkflowEngine.execute_workflow(wf.workflow_id)
    assert telemetry.execution_status == "AWAITING_USER_APPROVAL"
    assert telemetry.active_workflow.status == STATE_AWAITING_USER


# -------------------------
# RESTART RECOVERY TEST
# -------------------------
def test_workflow_restart_recovery():
    wf = AutonomousWorkflowEngine.create_workflow("Background Refactoring Objective")
    wf.status = "RUNNING"
    
    recovered = AutonomousWorkflowEngine.recover_workflows()
    assert any(r.workflow_id == wf.workflow_id for r in recovered)
