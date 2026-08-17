# Saki AI — Subsystem Integration Guide
**Sprint 20 Integration Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Unified System Integration  

---

## 1. SINGLE BRAIN CENTRAL ROUTING

All frontend API calls dispatches through `backend/routes/chat.py` (`/api/chat` and `/api/chat/stream`).

```
ChatRequest (message, conversation_id, mode)
    ↓
SakiModelOrchestrator.classify_request()
    ↓
PersonalContextEngine.select_minimal_context()
    ↓
UnifiedKnowledgeEngine.retrieve_knowledge()
    ↓
KnowledgeFusionEngine.fuse_knowledge()
    ↓
KnowledgeGraphEngine.traverse_subgraph()
    ↓
WebIntelligenceCapability.execute_web_intelligence() [If Web Query]
    ↓
AdaptiveIntelligenceEngine.process_user_input() [If Learning Signal]
    ↓
AutonomousWorkflowEngine.execute_workflow() [If Multi-step Workflow]
    ↓
PrivacyPolicyEngine Outbound Redaction
    ↓
ChatResponse (response, telemetry schemas)
```

---

## 2. CONSOLIDATED TELEMETRY SCHEMA

Every request returns consolidated subsystem telemetry via [`ChatResponse`](file:///c:/Users/gurus/work/saki/backend/models/schemas.py#L640):
- `action_decision`: ActionEngine telemetry
- `evidence_package`: EvidenceEngine telemetry
- `research_result`: ResearchPlanner telemetry
- `memory_admission`: MemoryAdmissionEngine telemetry
- `browser_observation`: BrowserController telemetry
- `computer_observation`: ComputerController telemetry
- `development_task`: DevelopmentCapability telemetry
- `git_github_telemetry`: GitGitHubCapability telemetry
- `persistent_task`: PersistentTaskCapability telemetry
- `personal_context`: PersonalContextEngine telemetry
- `unified_knowledge`: UnifiedKnowledgeEngine telemetry
- `knowledge_fusion`: KnowledgeFusionEngine telemetry
- `knowledge_graph`: KnowledgeGraphEngine telemetry
- `web_intelligence`: WebIntelligenceCapability telemetry
- `adaptive_intelligence`: AdaptiveIntelligenceEngine telemetry
- `autonomous_workflow`: AutonomousWorkflowEngine telemetry
