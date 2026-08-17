# Saki AI — System Architecture Specification (S0–S20)
**Version**: 20.0  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Unified Saki Intelligence Architecture  

---

## 1. ARCHITECTURAL LAW & SYSTEM FOUNDATION

Saki AI is **ONE integrated AI system** operating under a single cognitive authority (`SakiModelOrchestrator` in [`chat.py`](file:///c:/Users/gurus/work/saki/backend/routes/chat.py#L350)). There are **no competing brains, no secondary autonomous agents, no parallel memory stores, and no independent RAG engines**.

```
User Request
    ↓
Saki Central Brain (SakiModelOrchestrator in backend/routes/chat.py)
    ├── S1 Cognitive Action Engine (Taxonomy classification)
    ├── S2 Privacy Policy Boundary (Outbound firewall & secret redaction)
    ├── S3/S7/S16 Web Intelligence & DOM Browser (DDG search, WebFetcher, BrowserController)
    ├── S4/S14/S17 Evidence Intelligence & Knowledge Fusion (Claim verification & conflict check)
    ├── S6/S12 Personal Context & Memory Admission (Scoped minimal context selection)
    ├── S8/S9/S10 Computer, Development & Git/GitHub Capabilities (Sandboxed execution)
    ├── S11/S19 Persistent Tasks & Autonomous Workflows (Multi-step checkpointed execution)
    ├── S13/S15 Unified Knowledge & Knowledge Graph (Cross-source RAG & relationship graph)
    └── S18 Adaptive Intelligence (Scoped user preference admission & supersession)
    ↓
Grounded Response & Consolidated Telemetry (ChatResponse)
```

---

## 2. SUBSYSTEM TAXONOMY (S0–S20)

| Subsystem | Service File | Primary Role |
|---|---|---|
| S1 Action Engine | [`backend/services/action_engine.py`](file:///c:/Users/gurus/work/saki/backend/services/action_engine.py) | Structured 12-action taxonomy classification |
| S2 Privacy Boundary | [`backend/core/privacy.py`](file:///c:/Users/gurus/work/saki/backend/core/privacy.py) | Central outbound security boundary & PII/secret sanitizer |
| S3 World Access | [`backend/services/world_access_manager.py`](file:///c:/Users/gurus/work/saki/backend/services/world_access_manager.py) | SSRF-guarded DDG search & WebFetcher |
| S4 Evidence Engine | [`backend/services/evidence_engine.py`](file:///c:/Users/gurus/work/saki/backend/services/evidence_engine.py) | Evidence normalization, authority scoring & conflict check |
| S5 Research Planner | [`backend/services/research_planner.py`](file:///c:/Users/gurus/work/saki/backend/services/research_planner.py) | Query diversification & budget-bounded research loops |
| S6 Memory Admission | [`backend/services/memory_admission.py`](file:///c:/Users/gurus/work/saki/backend/services/memory_admission.py) | Durable memory admission & memory poisoning defense |
| S7 Browser Controller | [`backend/services/browser_controller.py`](file:///c:/Users/gurus/work/saki/backend/services/browser_controller.py) | DOM browser automation fallback for JS rendering |
| S8 Computer Controller | [`backend/services/computer_controller.py`](file:///c:/Users/gurus/work/saki/backend/services/computer_controller.py) | Workspace-sandboxed local CLI execution |
| S9 Development Capability | [`backend/services/development_capability.py`](file:///c:/Users/gurus/work/saki/backend/services/development_capability.py) | Repository scanning, code search & atomic rollbacks |
| S10 Git/GitHub Capability | [`backend/services/git_github_capability.py`](file:///c:/Users/gurus/work/saki/backend/services/git_github_capability.py) | Secret scanning commit guard & force push protection |
| S11 Persistent Tasks | [`backend/services/task_capability.py`](file:///c:/Users/gurus/work/saki/backend/services/task_capability.py) | Task state machine tracking & JSON persistence |
| S12 Personal Context | [`backend/services/personal_context.py`](file:///c:/Users/gurus/work/saki/backend/services/personal_context.py) | Minimal context budgeting (max 5 items) & attention policy |
| S13 Unified Knowledge | [`backend/services/unified_knowledge.py`](file:///c:/Users/gurus/work/saki/backend/services/unified_knowledge.py) | Single central multi-source RAG retrieval interface |
| S14 Knowledge Fusion | [`backend/services/knowledge_fusion.py`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_fusion.py) | Cross-source claim fusion & contradiction detection |
| S15 Knowledge Graph | [`backend/services/knowledge_graph.py`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_graph.py) | Bounded personal + project relationship graph |
| S16 Web Intelligence | [`backend/services/web_intelligence.py`](file:///c:/Users/gurus/work/saki/backend/services/web_intelligence.py) | Multi-step search & primary source discovery |
| S18 Adaptive Intelligence | [`backend/services/adaptive_intelligence.py`](file:///c:/Users/gurus/work/saki/backend/services/adaptive_intelligence.py) | Explicit user preference scoping & supersession |
| S19 Autonomous Workflows | [`backend/services/autonomous_workflow.py`](file:///c:/Users/gurus/work/saki/backend/services/autonomous_workflow.py) | Checkpointed multi-step workflow execution over S11 |
