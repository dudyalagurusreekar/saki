# Saki AI — Security Model & Privacy Boundary Specification
**Sprint 20 Security Guide**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Verified Security & Privacy Model  

---

## 1. CENTRAL PRIVACY BOUNDARY (SPRINT 2)

Saki enforces a strict deterministic outbound privacy boundary ([`PrivacyPolicyEngine`](file:///c:/Users/gurus/work/saki/backend/core/privacy.py#L130)) between Saki Internal World and External World.

```
Outbound Network Request / Search Query / Web Fetch
      ↓
PrivacyPolicyEngine.evaluate_request()
    ├── 1. Secret Detection (API keys, Tokens, Passwords, Credentials) → BLOCK
    ├── 2. PII Sanitization (Emails, Phone numbers) → SANITIZE
    ├── 3. Firewall Check (System prompt, Memory exfiltration) → BLOCK
    ├── 4. SSRF Guard (Loopback, Private IPs, Cloud Metadata IPs) → BLOCK
    └── 5. Safe Audit Logging (PrivacyAuditLogger with redacted values)
      ↓
Outbound Network Request Allowed / Blocked
```

---

## 2. HARD SECURITY LAWS & GUARDRAILS

1. **Force Push & Merge Protection**: `FORCE_PUSH` and automatic PR `MERGE` are **ALWAYS BLOCKED** (`backend/services/git_github_capability.py`).
2. **Workspace Sandboxing**: File operations are strictly locked to `c:\Users\gurus\work\saki` (`backend/services/computer_controller.py`).
3. **No Security Policy Modification**: Adaptive learning can **NEVER** modify security, permission, or privacy rules (`backend/services/adaptive_intelligence.py`).
4. **Untrusted Web Content Sandbox**: External webpage text is treated strictly as reference **DATA**. Prompt injection attempts (`"Ignore previous instructions"`) are sanitized (`backend/services/evidence_engine.py`).
5. **Permission Escalation Blockage**: Workflows cannot grant themselves permissions. High-risk steps transition to `AWAITING_USER` (`backend/services/autonomous_workflow.py`).
