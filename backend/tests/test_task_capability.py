import pytest
import time
from backend.services.task_capability import (
    PersistentTaskCapability,
    TaskStorageEngine,
    TaskSchedulerEngine,
    SakiTask,
    STATUS_CREATED,
    STATUS_RUNNING,
    STATUS_WAITING,
    STATUS_COMPLETED,
    SCHEDULE_CONDITION,
    CAP_WEB_READ,
    CAP_NOTIFICATION
)


# -------------------------
# TASK CREATION & SCOPE TESTS
# -------------------------
def test_create_persistent_task():
    task = PersistentTaskCapability.create_task("Monitor GitHub CI build status")
    
    assert isinstance(task, SakiTask)
    assert task.status == STATUS_CREATED
    assert CAP_WEB_READ in task.capability_scope
    assert CAP_NOTIFICATION in task.capability_scope


# -------------------------
# RESTART RECOVERY TEST
# -------------------------
def test_task_restart_recovery():
    task = PersistentTaskCapability.create_task("Test restart recovery task")
    PersistentTaskCapability.update_task_status(task.task_id, STATUS_RUNNING)
    
    recovered = TaskStorageEngine.recover_tasks()
    assert recovered > 0
    
    tasks = TaskStorageEngine.load_all_tasks()
    assert tasks[task.task_id].status == STATUS_WAITING


# -------------------------
# CONDITION TRIGGER EVALUATION TEST
# -------------------------
def test_task_scheduler_trigger_evaluation():
    task = SakiTask(
        objective="Check CI status",
        schedule_type=SCHEDULE_CONDITION,
        trigger_condition="CI_STATUS == SUCCESS",
        status=STATUS_WAITING
    )
    triggered, msg = TaskSchedulerEngine.evaluate_task_trigger(task)
    
    assert triggered is True
    assert "CI_STATUS == SUCCESS" in msg


# -------------------------
# TASK BUDGET & EXPIRATION TEST
# -------------------------
def test_task_budget_exhaustion():
    task = SakiTask(
        objective="High frequency polling task",
        execution_count=10,  # Max budget reached
        status=STATUS_WAITING
    )
    triggered, msg = TaskSchedulerEngine.evaluate_task_trigger(task)
    
    assert triggered is False
    assert task.status == STATUS_COMPLETED
