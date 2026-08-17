# Saki AI — Computer & OS Intelligence Subsystem Specification
**Sprint 8 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Computer Controller & OS Policy Engine  

---

## 1. SUBSYSTEM ARCHITECTURE

The Computer & OS Intelligence Subsystem provides sandboxed local environment inspection, workspace file reading, and code editing under strict workspace boundary and risk assessment policies:

```
              [ User Query / ChatRequest ]
                           │
                           ▼
          [ Cognitive Action Engine (Sprint 1) ]
                  (CODING / Inspection)
                           │
                           ▼
          [ PrivacyPolicyEngine (Sprint 2) ]
            (Outbound Request & Secret Filter)
                           │
                           ▼
         [ ComputerPolicyEngine (backend/services/computer_controller.py) ]
            ├── WORKSPACE_ROOT containment (c:\Users\gurus\work\saki)
            ├── Path Traversal Filter (Blocks '..')
            ├── Destructive Command Filter (Blocks rm -rf, del /f, format)
            └── Risk Assessment Matrix (RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_PROHIBITED)
                           │
                           ▼
         [ ComputerController & Workspace Sandbox ]
            (Reads workspace files, inspects dir structure, safe edits)
                           │
                           ▼
                 [ ComputerObservation ]
                           │
                           ▼
                [ Local LLMs (Phi-3/Qwen-3) ]
```

---

## 2. RISK ASSESSMENT MATRIX

| Risk Level | Operations Included | Handling / Policy |
|---|---|---|
| `RISK_LOW` | Listing workspace directories, reading workspace documentation/files | Authorized automatically inside workspace sandbox |
| `RISK_MEDIUM` | Editing existing workspace code files, running unit tests | Authorized within active workspace boundary |
| `RISK_HIGH` | Deleting files, modifying system files | Requires explicit user confirmation |
| `RISK_PROHIBITED` | Path traversal (`..`), accessing outside workspace (`C:\Windows`, `/etc`), formatting drives | **Strictly Blocked (`DECISION_BLOCK`)** |

---

## 3. WORKSPACE SANDBOXING & PATH TRAVERSAL DEFENSE

- **Workspace Root Boundary**: All file operations are restricted to `WORKSPACE_ROOT = c:\Users\gurus\work\saki`.
- **Path Traversal Protection**: Paths containing `..` or attempting to escape the workspace root resolve to `RISK_PROHIBITED` and return a security violation status.

---

## 4. PROHIBITED COMMAND FILTER

Commands matching any of the following patterns evaluate to `RISK_PROHIBITED` and are immediately halted:
`rm -rf`, `del /f`, `format `, `shutdown`, `reg delete`, `chmod -R 777`, `mkfs`, `dd if=`.

---

## 5. PRIVACY & SECRET MASKING

Before any local file content snippet is returned in a `ComputerObservation`, the content is evaluated by Sprint 2 `PrivacyPolicyEngine`. If secrets (API keys, credentials) are detected, they are automatically masked (`[Secret Protected Content Masked by Privacy Boundary]`).
