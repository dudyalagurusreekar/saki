# Saki AI — Integrated Git & GitHub Collaboration Specification
**Sprint 10 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Integrated Git/GitHub Collaboration Capability  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Integrated Git/GitHub Collaboration Capability (`GitGitHubCapability`) is a capability module within Saki's existing central orchestrator—**NOT a secondary agent (`GitHubAgent`, `PRAgent`), second orchestrator, or parallel coding brain**.

All Git and GitHub operations reuse Saki's existing infrastructure:
- **Central Decision Maker**: `SakiModelOrchestrator` ([`backend/routes/chat.py`](file:///c:/Users/gurus/work/saki/backend/routes/chat.py#L350))
- **Action Engine**: Sprint 1 Action Decision (`GIT_STATUS`, `COMMIT_CHANGES`, `PUSH_BRANCH`, `CREATE_DRAFT_PR`)
- **Privacy Engine**: Sprint 2 secret scanning & outbound validation
- **Evidence Engine**: Sprint 4 XML prompt isolation (`<external_web_content>`) for issue/review text
- **Development Capability**: Sprint 9 RepositoryScanner & CodeSearchEngine
- **Computer Controller**: Sprint 8 workspace sandbox & command risk policy

```
USER REQUEST
     ↓
SAKI CENTRAL BRAIN (SakiModelOrchestrator in chat.py)
     ↓
ACTION ENGINE (Sprint 1: GIT_STATUS, COMMIT_CHANGES, PUSH_BRANCH, CREATE_DRAFT_PR)
     ↓
GIT/GITHUB CAPABILITY (backend/services/git_github_capability.py)
     ├── 1. RepositoryAllowlistGuard (Restricts operations to dudyalagurusreekar/saki)
     ├── 2. GitCapability (Status, branch, secret-scanned commit, push permission check)
     ├── 3. Secret Scanning Commit Guard (Blocks commit if API key/token detected)
     ├── 4. Force Push Guard (FORCE_PUSH = ALWAYS BLOCKED)
     ├── 5. GitHubCapability (Issue/PR inspection, CI tracking, draft PR preparation)
     └── 6. PR Merge Guard (Self-approval & automatic PR merges = ALWAYS BLOCKED)
     ↓
LOCAL LLM ANSWER GENERATION & TELEMETRY
```

---

## 2. SECURITY GUARDRAILS MATRIX

| Operation | Permission Mode | User Confirmation Required | Security Safeguard |
|---|---|---|---|
| `GIT_STATUS` / `DIFF` | `READ_ONLY` | No (Automatic) | Read-only inspection within workspace |
| `CREATE_BRANCH` | `LOW` | No (Automatic) | Naming sanitization (`feature/name`) |
| `CREATE_COMMIT` | `MEDIUM` | No (Automatic) | **Secret Scanning Guard**: Scans staged content for API keys/tokens; blocks commit if secret detected |
| `PUSH_BRANCH` | `HIGH` | **Yes (Required)** | **Force Push Protection**: `git push --force` is **ALWAYS BLOCKED**. Protected branches (`main`) require explicit approval |
| `CREATE_DRAFT_PR` | `HIGH` | **Yes (Required)** | **Draft PR by Default**: Creates draft PRs. Self-approval and automatic PR merges are **ALWAYS BLOCKED** |

---

## 3. STATE MACHINE & TELEMETRY

```
LOCAL_VERIFIED ──► REMOTE_NOT_UPDATED ──► PR_PENDING ──► CI_PASSED / CI_FAILED ──► COMPLETED
```

Telemetry object (`GitGitHubTelemetry`) is exposed in `ChatResponse.git_github_telemetry` for complete frontend visibility.
