import pytest
from pathlib import Path
from backend.services.development_capability import (
    DevelopmentCapability,
    RepositoryScanner,
    CodeSearchEngine,
    SecretRedactor,
    DevelopmentTask,
    STATUS_COMPLETED,
    RISK_LOW
)
from backend.services.computer_controller import WORKSPACE_ROOT


# -------------------------
# REPOSITORY SCANNER TESTS
# -------------------------
def test_repository_scanner_discovers_structure():
    ctx = RepositoryScanner.scan_repository()
    
    assert ctx.repository_id == "saki"
    assert "backend" in ctx.source_directories
    assert "backend/tests" in ctx.test_directories
    assert len(ctx.configuration_files) > 0


# -------------------------
# SECRET REDACTION TESTS
# -------------------------
def test_secret_redactor_masks_credentials():
    code_snippet = 'API_KEY = "AIzaSyBJej43jDBLEVqbjp4GH6UfSRktBl6hrnc"'
    redacted = SecretRedactor.redact_code(code_snippet)
    
    assert "AIzaSy" not in redacted
    assert "[SECRET REDACTED]" in redacted


# -------------------------
# CODE SEARCH TESTS
# -------------------------
def test_code_search_engine_returns_snippets():
    results = CodeSearchEngine.search_workspace("FastAPI", max_matches=3)
    
    assert isinstance(results, list)
    assert len(results) > 0
    assert "file" in results[0]
    assert "snippet" in results[0]


# -------------------------
# DEVELOPMENT TASK EXECUTION TESTS
# -------------------------
def test_execute_development_task_flow():
    user_req = "Inspect chat routes for bug fix"
    task = DevelopmentCapability.execute_development_task(user_req)
    
    assert isinstance(task, DevelopmentTask)
    assert task.status == STATUS_COMPLETED
    assert task.plan is not None
    assert len(task.plan.steps) == 5
    assert task.tests_passed is True


# -------------------------
# ATOMIC ROLLBACK TESTS
# -------------------------
def test_atomic_rollback_mechanism(tmp_path):
    test_file = WORKSPACE_ROOT / "scratch_test_rollback.txt"
    test_file.write_text("original baseline content", encoding="utf-8")
    
    # Save checkpoint & mutate
    DevelopmentCapability._rollbacks[str(test_file)] = "original baseline content"
    test_file.write_text("mutated content", encoding="utf-8")
    
    # Execute Rollback
    success, msg = DevelopmentCapability.rollback_file(str(test_file))
    
    assert success is True
    assert test_file.read_text(encoding="utf-8") == "original baseline content"
    
    # Cleanup scratch file
    if test_file.exists():
        test_file.unlink()
