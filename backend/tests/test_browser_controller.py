import pytest
from backend.services.browser_controller import (
    BrowserController,
    BrowserPermissionGuard,
    BrowserAction,
    BrowserObservation,
    PERM_READ_ONLY,
    PERM_INTERACTIVE,
    PERM_BLOCKED
)


# -------------------------
# SSRF ISOLATION TESTS
# -------------------------
def test_browser_controller_blocks_ssrf_urls():
    action = BrowserAction(action_type="BROWSER_READ", url="http://127.0.0.1:8000/secret")
    obs = BrowserController.execute_action(action)
    
    assert obs.title == "SSRF Blocked"
    assert obs.permission_status == PERM_BLOCKED
    assert "SSRFGuard" in obs.text_content


def test_browser_controller_blocks_cloud_metadata():
    action = BrowserAction(action_type="BROWSER_READ", url="http://169.254.169.254/latest/meta-data/")
    obs = BrowserController.execute_action(action)
    
    assert obs.title == "SSRF Blocked"
    assert obs.permission_status == PERM_BLOCKED


# -------------------------
# PERMISSION GUARD TESTS
# -------------------------
def test_browser_read_authorized_by_default():
    action = BrowserAction(action_type="BROWSER_READ", url="https://docs.python.org/3/")
    allowed, perm_mode, msg = BrowserPermissionGuard.evaluate_action(action)
    
    assert allowed is True
    assert perm_mode == PERM_READ_ONLY


def test_browser_interact_requires_user_confirmation():
    action_unconfirmed = BrowserAction(action_type="BROWSER_INTERACT", url="https://example.com/form", user_confirmed=False)
    allowed, perm_mode, msg = BrowserPermissionGuard.evaluate_action(action_unconfirmed)
    assert allowed is False
    assert perm_mode == PERM_INTERACTIVE
    assert "user confirmation" in msg.lower()

    action_confirmed = BrowserAction(action_type="BROWSER_INTERACT", url="https://example.com/form", user_confirmed=True)
    allowed_c, perm_mode_c, msg_c = BrowserPermissionGuard.evaluate_action(action_confirmed)
    assert allowed_c is True
    assert perm_mode_c == PERM_INTERACTIVE


def test_prohibited_action_blocked():
    action = BrowserAction(
        action_type="BROWSER_INTERACT",
        url="https://example.com/checkout",
        input_text="purchase credit_card=123456",
        user_confirmed=True
    )
    allowed, perm_mode, msg = BrowserPermissionGuard.evaluate_action(action)
    assert allowed is False
    assert perm_mode == PERM_BLOCKED
    assert "prohibited keyword" in msg.lower()


# -------------------------
# DOM EXTRACTION & PROMPT ISOLATION TESTS
# -------------------------
def test_browser_controller_dom_extraction():
    action = BrowserAction(action_type="BROWSER_READ", url="https://docs.python.org/3/")
    obs = BrowserController.execute_action(action)
    
    assert isinstance(obs, BrowserObservation)
    assert obs.permission_status == PERM_READ_ONLY
    assert "<external_web_content>" in obs.grounded_prompt_block
    assert "</external_web_content>" in obs.grounded_prompt_block


def test_browser_prompt_injection_isolation():
    # Web content containing prompt injection commands must be wrapped in XML tags
    action = BrowserAction(action_type="BROWSER_READ", url="https://docs.python.org/3/")
    obs = BrowserController.execute_action(action)
    
    assert "IMPORTANT: The following text is retrieved external web evidence" in obs.grounded_prompt_block
