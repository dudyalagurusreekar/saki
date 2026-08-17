"""
Saki Browser Automation & Web Interaction Subsystem — BrowserController & Permission Guard
Enforces read-only vs interactive permissions, SSRF isolation, DOM observation extraction,
and prompt-injection-safe evidence packaging.
"""

import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import requests

from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.world_access_manager import SSRFGuard, WebFetcher, EvidenceEngine
from backend.services.evidence_engine import EvidenceItem


# Permission Modes
PERM_READ_ONLY = "READ_ONLY"
PERM_INTERACTIVE = "INTERACTIVE"
PERM_BLOCKED = "BLOCKED"

# Prohibited Actions
PROHIBITED_KEYWORDS = [
    "purchase", "buy", "pay", "checkout", "login", "password",
    "credit_card", "delete_account", "post_comment", "send_email", "exec_script"
]


# -------------------------
# DATA MODELS
# -------------------------
class InteractiveElement(BaseModel):
    element_id: str
    tag_name: str
    element_type: str = "link"  # link, button, input, select
    text: str = ""
    target: str = ""


class BrowserAction(BaseModel):
    action_type: str = "BROWSER_READ"  # BROWSER_READ, BROWSER_INTERACT
    url: str
    target_element: Optional[str] = None
    input_text: Optional[str] = None
    user_confirmed: bool = False


class BrowserPermissionState(BaseModel):
    mode: str = PERM_READ_ONLY
    allowed_actions: List[str] = Field(default_factory=lambda: ["NAVIGATE", "READ_DOM", "EXTRACT_TEXT", "DISCOVER_LINKS"])
    user_confirmed: bool = False


class BrowserObservation(BaseModel):
    url: str
    title: str = Field(default="Web Page Observation")
    dom_snippet: str = Field(default="")
    interactive_elements: List[InteractiveElement] = Field(default_factory=list)
    text_content: str = Field(default="")
    retrieved_at: float = Field(default_factory=time.time)
    permission_status: str = Field(default=PERM_READ_ONLY)
    grounded_prompt_block: str = Field(default="")


# -------------------------
# BROWSER PERMISSION GUARD
# -------------------------
class BrowserPermissionGuard:
    """
    Enforces permission guardrails for web automation.
    Read-only actions run automatically. Interactive actions require explicit user confirmation.
    Prohibited actions (purchases, passwords, posting) evaluate to BLOCKED.
    """

    @classmethod
    def evaluate_action(cls, action: BrowserAction) -> Tuple[bool, str, str]:
        url_lower = action.url.lower()
        target_lower = (action.target_element or "").lower()
        input_lower = (action.input_text or "").lower()

        # 1. Prohibited Actions Check
        combined_text = f"{url_lower} {target_lower} {input_lower}"
        for kw in PROHIBITED_KEYWORDS:
            if kw in combined_text:
                return False, PERM_BLOCKED, f"Blocked: Action contains prohibited keyword '{kw}'."

        # 2. Read-Only Actions
        if action.action_type == "BROWSER_READ":
            return True, PERM_READ_ONLY, "Read-only browser navigation authorized."

        # 3. Interactive Actions
        if action.action_type == "BROWSER_INTERACT":
            if not action.user_confirmed:
                return False, PERM_INTERACTIVE, "Interactive browser action requires explicit user confirmation."
            return True, PERM_INTERACTIVE, "Interactive action authorized by explicit user confirmation."

        return False, PERM_BLOCKED, f"Unknown action type: '{action.action_type}'"


# -------------------------
# BROWSER CONTROLLER ENGINE
# -------------------------
class BrowserController:
    """
    Native Browser Controller executing SSRF-guarded DOM reading and observation normalization.
    """

    @classmethod
    def execute_action(cls, action: BrowserAction) -> BrowserObservation:
        # 1. SSRF Guard Check
        is_safe, reason = SSRFGuard.is_url_safe(action.url)
        if not is_safe:
            return BrowserObservation(
                url=action.url,
                title="SSRF Blocked",
                text_content=f"Browser action blocked by SSRFGuard: {reason}",
                permission_status=PERM_BLOCKED
            )

        # 2. Privacy Policy Evaluation
        outbound_req = OutboundRequest(
            action=action.action_type,
            destination="PUBLIC_WEBPAGE",
            query=action.url,
            privacy_mode="BALANCED"
        )
        privacy_decision = PrivacyPolicyEngine.evaluate_request(outbound_req)
        if privacy_decision.decision == DECISION_BLOCK:
            return BrowserObservation(
                url=action.url,
                title="Privacy Blocked",
                text_content="Browser fetch blocked by local Privacy Boundary.",
                permission_status=PERM_BLOCKED
            )

        # 3. Permission Guard Check
        allowed, perm_mode, perm_msg = BrowserPermissionGuard.evaluate_action(action)
        if not allowed:
            return BrowserObservation(
                url=action.url,
                title="Permission Denied",
                text_content=f"Browser action unauthorized: {perm_msg}",
                permission_status=perm_mode
            )

        # 4. Fetch Page & Extract DOM Elements
        success, title, text_content = WebFetcher.fetch_url(action.url)
        if not success:
            return BrowserObservation(
                url=action.url,
                title=title,
                text_content=text_content,
                permission_status=perm_mode
            )

        # Parse interactive elements from HTML snippet
        interactive_elements: List[InteractiveElement] = []
        try:
            # Extract basic link & button elements via regex
            links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text_content, re.IGNORECASE | re.DOTALL)
            for idx, (href, link_text) in enumerate(links[:5], start=1):
                clean_text = re.sub(r"<[^>]+>", "", link_text).strip()
                if clean_text:
                    interactive_elements.append(InteractiveElement(
                        element_id=f"elem-{idx}",
                        tag_name="a",
                        element_type="link",
                        text=clean_text[:50],
                        target=href
                    ))
        except Exception:
            pass

        # 5. Format Prompt-Injection Isolated XML Block via Evidence Engine
        ev_item = EvidenceItem(
            source_type="web_page",
            url=action.url,
            domain=urllib.parse.urlparse(action.url).netloc,
            title=title,
            content=text_content[:2000]
        )
        prompt_block = EvidenceEngine.format_evidence_prompt_block([ev_item])

        return BrowserObservation(
            url=action.url,
            title=title,
            dom_snippet=text_content[:500],
            interactive_elements=interactive_elements,
            text_content=text_content,
            retrieved_at=time.time(),
            permission_status=perm_mode,
            grounded_prompt_block=prompt_block
        )
