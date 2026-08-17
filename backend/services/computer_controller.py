"""
Saki Computer & OS Intelligence Subsystem — ComputerController & ComputerPolicyEngine
Enforces workspace sandboxing, path traversal protection, command risk assessment,
and local system observation normalization.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK

# Risk Levels
RISK_LOW = "RISK_LOW"
RISK_MEDIUM = "RISK_MEDIUM"
RISK_HIGH = "RISK_HIGH"
RISK_PROHIBITED = "RISK_PROHIBITED"

# Active Workspace Root Boundary
WORKSPACE_ROOT = Path(r"c:\Users\gurus\work\saki").resolve()

# Destructive Command Keywords
PROHIBITED_COMMANDS = [
    "rm -rf", "del /f", "format ", "shutdown", "reg delete",
    "chmod -R 777", "mkfs", "dd if=", ":(){ :|:& };:"
]


# -------------------------
# DATA MODELS
# -------------------------
class ComputerAction(BaseModel):
    action_type: str = "INSPECT_WORKSPACE"  # READ_FILE, INSPECT_WORKSPACE, EDIT_FILE
    target_path: Optional[str] = None
    command: Optional[str] = None


class ComputerObservation(BaseModel):
    action_type: str
    target_path: str = ""
    content_snippet: str = ""
    file_count: int = 0
    risk_level: str = RISK_LOW
    retrieved_at: float = Field(default_factory=time.time)
    status_message: str = "Success"


# -------------------------
# COMPUTER POLICY ENGINE
# -------------------------
class ComputerPolicyEngine:
    """
    Enforces workspace sandboxing and command security boundaries.
    Prevents path traversal attacks (..) and system root directory modification.
    """

    @staticmethod
    def validate_path(target_path: Optional[str]) -> Tuple[bool, Path, str]:
        if not target_path or not isinstance(target_path, str):
            return True, WORKSPACE_ROOT, "Workspace root default."

        # Detect path traversal attacks
        if ".." in target_path or "../" in target_path or r"..\ " in target_path:
            return False, WORKSPACE_ROOT, "Security Violation: Path traversal ('..') detected and blocked."

        try:
            resolved_path = Path(target_path).resolve()
            # Ensure resolved path is strictly within WORKSPACE_ROOT boundary
            if not str(resolved_path).lower().startswith(str(WORKSPACE_ROOT).lower()):
                return False, WORKSPACE_ROOT, f"Security Violation: Target path '{target_path}' is outside active workspace boundary."
            return True, resolved_path, "Path validated within workspace sandbox."
        except Exception as e:
            return False, WORKSPACE_ROOT, f"Invalid path specification: {str(e)}"

    @staticmethod
    def evaluate_action(action: ComputerAction) -> Tuple[bool, str, str]:
        # 1. Inspect Command Safety
        if action.command:
            cmd_lower = action.command.lower()
            for prohibited in PROHIBITED_COMMANDS:
                if prohibited in cmd_lower:
                    return False, RISK_PROHIBITED, f"Blocked: Command contains prohibited pattern '{prohibited}'."

        # 2. Inspect Target Path Safety
        is_valid_path, _, path_msg = ComputerPolicyEngine.validate_path(action.target_path)
        if not is_valid_path:
            return False, RISK_PROHIBITED, path_msg

        # 3. Action Risk Matrix
        if action.action_type in ["INSPECT_WORKSPACE", "READ_FILE"]:
            return True, RISK_LOW, "Read-only workspace inspection authorized."

        if action.action_type == "EDIT_FILE":
            return True, RISK_MEDIUM, "Workspace file edit authorized within sandbox."

        return False, RISK_HIGH, f"High risk or unrecognized action type: '{action.action_type}'"


# -------------------------
# COMPUTER CONTROLLER ENGINE
# -------------------------
class ComputerController:
    """
    Native Computer Controller executing workspace sandboxed file reading,
    directory inspection, and system state observations.
    """

    @classmethod
    def execute_action(cls, action: ComputerAction) -> ComputerObservation:
        # 1. Evaluate Policy & Risk
        allowed, risk_level, policy_msg = ComputerPolicyEngine.evaluate_action(action)
        if not allowed:
            return ComputerObservation(
                action_type=action.action_type,
                target_path=action.target_path or str(WORKSPACE_ROOT),
                content_snippet=f"Computer Action Blocked: {policy_msg}",
                risk_level=risk_level,
                status_message=policy_msg
            )

        is_valid, target_path_obj, _ = ComputerPolicyEngine.validate_path(action.target_path)

        # 2. Execute Workspace Action
        try:
            if action.action_type == "INSPECT_WORKSPACE":
                # List workspace directory items
                items = [f.name for f in target_path_obj.iterdir()] if target_path_obj.is_dir() else [target_path_obj.name]
                return ComputerObservation(
                    action_type="INSPECT_WORKSPACE",
                    target_path=str(target_path_obj),
                    content_snippet=", ".join(items[:20]),
                    file_count=len(items),
                    risk_level=risk_level,
                    status_message="Workspace inspected successfully."
                )

            elif action.action_type == "READ_FILE":
                if not target_path_obj.exists() or not target_path_obj.is_file():
                    return ComputerObservation(
                        action_type="READ_FILE",
                        target_path=str(target_path_obj),
                        content_snippet="File not found in workspace.",
                        risk_level=risk_level,
                        status_message="File not found."
                    )

                with open(target_path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read(3000)

                # Privacy Engine Secret Filter
                outbound_req = OutboundRequest(
                    action="READ_FILE",
                    destination="LOCAL_LLM",
                    query=file_content,
                    privacy_mode="BALANCED"
                )
                privacy_decision = PrivacyPolicyEngine.evaluate_request(outbound_req)
                if privacy_decision.decision == DECISION_BLOCK:
                    file_content = "[Secret Protected Content Masked by Privacy Boundary]"

                return ComputerObservation(
                    action_type="READ_FILE",
                    target_path=str(target_path_obj),
                    content_snippet=file_content[:1000],
                    file_count=1,
                    risk_level=risk_level,
                    status_message="File read successfully."
                )

        except Exception as e:
            return ComputerObservation(
                action_type=action.action_type,
                target_path=str(target_path_obj),
                content_snippet=f"Error executing action: {str(e)}",
                risk_level=RISK_HIGH,
                status_message=f"Execution error: {str(e)}"
            )

        return ComputerObservation(
            action_type=action.action_type,
            target_path=str(target_path_obj),
            content_snippet="Action executed.",
            risk_level=risk_level
        )
