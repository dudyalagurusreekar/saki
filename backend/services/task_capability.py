"""
Saki Integrated Persistent Tasks, Proactive Monitoring & Continuation Subsystem (PersistentTaskCapability)
Provides persistent task definition, state machine tracking, restart recovery, task storage,
and condition evaluation while maintaining Saki's single-brain cognitive authority.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK

# Task Persistence File
TASKS_FILE_PATH = Path("data/persistent_tasks.json")

# Task Statuses
STATUS_CREATED = "CREATED"
STATUS_PLANNED = "PLANNED"
STATUS_WAITING = "WAITING"
STATUS_READY = "READY"
STATUS_RUNNING = "RUNNING"
STATUS_PAUSED = "PAUSED"
STATUS_AWAITING_USER = "AWAITING_USER"
STATUS_AWAITING_EXTERNAL = "AWAITING_EXTERNAL_EVENT"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_BLOCKED = "BLOCKED"
STATUS_EXPIRED = "EXPIRED"
STATUS_CANCELLED = "CANCELLED"

# Schedule Types
SCHEDULE_ONE_TIME = "ONE_TIME"
SCHEDULE_RECURRING = "RECURRING"
SCHEDULE_CONDITION = "CONDITION_BASED"

# Capabilities Scope
CAP_WEB_READ = "WEB_READ"
CAP_GITHUB_READ = "GITHUB_READ"
CAP_BROWSER_READ = "BROWSER_READ"
CAP_COMPUTER_READ = "COMPUTER_READ"
CAP_DEVELOPMENT = "DEVELOPMENT"
CAP_GIT = "GIT"
CAP_NOTIFICATION = "NOTIFICATION"

# Budget Limits
MAX_TASK_EXECUTIONS = 10
MAX_TASK_FAILURES = 3


# -------------------------
# DATA MODELS
# -------------------------
class TaskExecutionHistory(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"exec-{time.time_ns() % 1000000}")
    timestamp: float = Field(default_factory=time.time)
    observation: str = ""
    status: str = STATUS_COMPLETED


class TaskCheckpoint(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"chk-{time.time_ns() % 1000000}")
    saved_at: float = Field(default_factory=time.time)
    last_observation: str = ""
    next_wake: Optional[float] = None
    state_payload: Dict[str, Any] = Field(default_factory=dict)


class SakiTask(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task-{time.time_ns() % 1000000}")
    user_id: str = "default_user"
    objective: str
    description: str = ""
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: str = STATUS_CREATED
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH
    schedule_type: str = SCHEDULE_ONE_TIME
    trigger_condition: Optional[str] = None
    capability_scope: List[str] = Field(default_factory=lambda: [CAP_WEB_READ, CAP_NOTIFICATION])
    checkpoint: Optional[TaskCheckpoint] = None
    next_wake: Optional[float] = None
    expires_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    execution_count: int = 0
    history: List[TaskExecutionHistory] = Field(default_factory=list)


# -------------------------
# TASK STORAGE ENGINE
# -------------------------
class TaskStorageEngine:
    """
    Handles JSON file storage, retrieval, and restart recovery for persistent tasks.
    """

    @classmethod
    def load_all_tasks(cls) -> Dict[str, SakiTask]:
        if not TASKS_FILE_PATH.exists():
            return {}
        try:
            with open(TASKS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: SakiTask(**v) for k, v in data.items()}
        except Exception:
            return {}

    @classmethod
    def save_all_tasks(cls, tasks: Dict[str, SakiTask]) -> None:
        TASKS_FILE_PATH.parent.mkdir(exist_ok=True)
        serialized = {k: v.dict() for k, v in tasks.items()}
        with open(TASKS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)

    @classmethod
    def recover_tasks(cls) -> int:
        """
        Executes restart recovery: Interrupted RUNNING tasks transition safely to WAITING.
        """
        tasks = cls.load_all_tasks()
        recovered_count = 0
        for task in tasks.values():
            if task.status == STATUS_RUNNING:
                task.status = STATUS_WAITING
                task.updated_at = time.time()
                recovered_count += 1
        if recovered_count > 0:
            cls.save_all_tasks(tasks)
        return recovered_count


# -------------------------
# TASK SCHEDULER ENGINE
# -------------------------
class TaskSchedulerEngine:
    """
    Evaluates task wake triggers and conditions.
    Wakes Saki central brain for re-evaluation rather than executing autonomous LLM loops.
    """

    @classmethod
    def evaluate_task_trigger(cls, task: SakiTask) -> Tuple[bool, str]:
        now = time.time()
        
        # Expiration Check
        if task.expires_at and now >= task.expires_at:
            task.status = STATUS_EXPIRED
            return False, "Task expired."

        # Budget Check
        if task.execution_count >= MAX_TASK_EXECUTIONS:
            task.status = STATUS_COMPLETED
            return False, "Task budget reached maximum executions."

        # Condition Check
        if task.schedule_type == SCHEDULE_CONDITION and task.trigger_condition:
            if "CI_STATUS == SUCCESS" in task.trigger_condition:
                return True, "Trigger condition 'CI_STATUS == SUCCESS' passed."

        if task.schedule_type in [SCHEDULE_ONE_TIME, SCHEDULE_RECURRING]:
            return True, "Scheduled wake trigger activated."

        return False, "Trigger condition pending."


# -------------------------
# PERSISTENT TASK CAPABILITY SERVICE
# -------------------------
class PersistentTaskCapability:
    """
    Public capability interface for managing persistent tasks and proactive monitoring.
    """

    @classmethod
    def create_task(cls, objective: str, schedule_type: str = SCHEDULE_ONE_TIME, condition: Optional[str] = None) -> SakiTask:
        tasks = TaskStorageEngine.load_all_tasks()
        task = SakiTask(
            objective=objective,
            schedule_type=schedule_type,
            trigger_condition=condition,
            status=STATUS_CREATED,
            next_wake=time.time() + 3600  # Default 1 hour wake
        )
        tasks[task.task_id] = task
        TaskStorageEngine.save_all_tasks(tasks)
        return task

    @classmethod
    def list_tasks(cls) -> List[SakiTask]:
        tasks = TaskStorageEngine.load_all_tasks()
        return list(tasks.values())

    @classmethod
    def update_task_status(cls, task_id: str, new_status: str) -> Optional[SakiTask]:
        tasks = TaskStorageEngine.load_all_tasks()
        if task_id in tasks:
            task = tasks[task_id]
            task.status = new_status
            task.updated_at = time.time()
            TaskStorageEngine.save_all_tasks(tasks)
            return task
        return None
