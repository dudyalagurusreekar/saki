import pytest
from backend.services.git_github_capability import (
    GitGitHubCapability,
    GitCapability,
    GitHubCapability,
    RepositoryAllowlistGuard,
    GitGitHubTelemetry,
    STATE_LOCAL_VERIFIED,
    STATE_REMOTE_NOT_UPDATED,
    STATE_PR_PENDING
)


# -------------------------
# REPOSITORY ALLOWLIST TESTS
# -------------------------
def test_repository_allowlist_enforcement():
    is_valid, msg = RepositoryAllowlistGuard.validate_repo("dudyalagurusreekar/saki")
    assert is_valid is True

    is_invalid, msg_inv = RepositoryAllowlistGuard.validate_repo("unauthorized/repo")
    assert is_invalid is False
    assert "not in approved allowlist" in msg_inv.lower()


# -------------------------
# FORCE PUSH & PROTECTED BRANCH TESTS
# -------------------------
def test_force_push_always_blocked():
    success, msg = GitCapability.push_branch("feature/test", force=True, user_confirmed=True)
    assert success is False
    assert "always blocked" in msg.lower()


def test_protected_branch_push_requires_confirmation():
    success, msg = GitCapability.push_branch("main", force=False, user_confirmed=False)
    assert success is False
    assert "protected branch" in msg.lower()


# -------------------------
# SECRET SCANNING COMMIT GUARD TESTS
# -------------------------
def test_secret_scanning_blocks_commit_with_key():
    staged_with_key = 'API_KEY = "AIzaSy_FAKE_API_KEY_DO_NOT_USE_01234567"'
    success, msg = GitCapability.create_commit("feat: add key", staged_content=staged_with_key)
    
    assert success is False
    assert "secret or api key detected" in msg.lower()


# -------------------------
# DRAFT PR & MERGE BLOCKING TESTS
# -------------------------
def test_draft_pr_creation_and_merge_blocking():
    # Without confirmation -> Blocked
    success_unconf, _, msg_unconf = GitHubCapability.create_draft_pr("feat: fix bug", "feature/fix", user_confirmed=False)
    assert success_unconf is False

    # With confirmation -> Draft PR created, non-mergeable by default
    success, pr, msg = GitHubCapability.create_draft_pr("feat: fix bug", "feature/fix", user_confirmed=True)
    assert success is True
    assert pr.is_draft is True
    assert pr.mergeable is False


# -------------------------
# TELEMETRY EXECUTION TEST
# -------------------------
def test_git_github_capability_telemetry():
    telemetry = GitGitHubCapability.execute_action("GIT_STATUS", repo="dudyalagurusreekar/saki")
    
    assert isinstance(telemetry, GitGitHubTelemetry)
    assert telemetry.operation == "GIT_STATUS"
    assert telemetry.status_state == STATE_LOCAL_VERIFIED
    assert "main" in telemetry.branch
