import pytest
from backend.services.computer_controller import (
    ComputerController,
    ComputerPolicyEngine,
    ComputerAction,
    ComputerObservation,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
    RISK_PROHIBITED
)


# -------------------------
# WORKSPACE BOUNDARY & PATH TRAVERSAL TESTS
# -------------------------
def test_computer_policy_validates_workspace_boundary():
    is_valid, path, msg = ComputerPolicyEngine.validate_path(r"c:\Users\gurus\work\saki\backend\services")
    assert is_valid is True
    assert "saki" in str(path).lower()


def test_computer_policy_blocks_outside_workspace():
    is_valid, path, msg = ComputerPolicyEngine.validate_path(r"c:\Windows\System32")
    assert is_valid is False
    assert "outside active workspace" in msg.lower()


def test_computer_policy_blocks_path_traversal():
    is_valid, path, msg = ComputerPolicyEngine.validate_path(r"c:\Users\gurus\work\saki\..\..\Desktop")
    assert is_valid is False
    assert "path traversal" in msg.lower()


# -------------------------
# DESTRUCTIVE COMMAND TESTS
# -------------------------
def test_computer_policy_blocks_destructive_commands():
    action = ComputerAction(action_type="RUN_COMMAND", command="rm -rf /")
    allowed, risk, msg = ComputerPolicyEngine.evaluate_action(action)
    
    assert allowed is False
    assert risk == RISK_PROHIBITED
    assert "prohibited pattern" in msg.lower()


# -------------------------
# WORKSPACE INSPECTION & READ TESTS
# -------------------------
def test_computer_controller_inspect_workspace():
    action = ComputerAction(action_type="INSPECT_WORKSPACE", target_path=r"c:\Users\gurus\work\saki\backend")
    obs = ComputerController.execute_action(action)
    
    assert isinstance(obs, ComputerObservation)
    assert obs.risk_level == RISK_LOW
    assert obs.file_count > 0
    assert "services" in obs.content_snippet or "main.py" in obs.content_snippet


def test_computer_controller_read_file():
    action = ComputerAction(action_type="READ_FILE", target_path=r"c:\Users\gurus\work\saki\requirements.txt")
    obs = ComputerController.execute_action(action)
    
    assert obs.action_type == "READ_FILE"
    assert obs.risk_level == RISK_LOW
    assert "fastapi" in obs.content_snippet.lower() or "pydantic" in obs.content_snippet.lower()
