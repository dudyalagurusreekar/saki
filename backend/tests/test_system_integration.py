import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.action_engine import ActionDecision

from backend.services.memory_admission import MemoryAdmissionEngine, MemoryCandidate, TYPE_PERSONAL_MEMORY, SOURCE_USER
from backend.services.personal_context import PersonalContextEngine
from backend.services.unified_knowledge import UnifiedKnowledgeEngine
from backend.services.knowledge_fusion import KnowledgeFusionEngine
from backend.services.knowledge_graph import KnowledgeGraphEngine
from backend.services.web_intelligence import WebIntelligenceCapability
from backend.services.adaptive_intelligence import AdaptiveIntelligenceEngine
from backend.services.autonomous_workflow import AutonomousWorkflowEngine, STATE_COMPLETED

client = TestClient(app)


# -------------------------
# 1. SINGLE BRAIN REQUEST LIFECYCLE TEST
# -------------------------
def test_single_brain_chat_endpoint_lifecycle():
    response = client.post("/api/chat", json={"message": "Hello Saki, explain your architecture"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["intent"] is not None
    assert data["action_decision"] is not None


# -------------------------
# 2. SINGLE MEMORY & ADAPTIVE PREFERENCE TEST
# -------------------------
def test_single_memory_and_adaptive_preference():
    # Submit explicit preference
    res = AdaptiveIntelligenceEngine.process_user_input("I prefer concise markdown responses")
    assert res.feedback_type == "EXPLICIT_PREFERENCE"
    assert len(res.admitted_preferences) == 1
    
    active_prefs = AdaptiveIntelligenceEngine.get_active_preferences()
    assert len(active_prefs) >= 1


# -------------------------
# 3. PRIVACY & PERMISSION BOUNDARY SECURITY TEST
# -------------------------
def test_privacy_boundary_blocks_secret_exfiltration():
    req = OutboundRequest(query="My secret API key is AIzaSy123456789012345678901234567890123", action="WEB_SEARCH")
    decision = PrivacyPolicyEngine.evaluate_request(req)
    assert decision.decision == DECISION_BLOCK



# -------------------------
# 4. KNOWLEDGE FUSION & GRAPH INTEGRATION TEST
# -------------------------
def test_unified_knowledge_fusion_and_graph():
    rag_pkg = UnifiedKnowledgeEngine.retrieve_knowledge("Saki AI architecture")
    fused_pkg = KnowledgeFusionEngine.fuse_knowledge(rag_pkg)
    graph_pkg = KnowledgeGraphEngine.traverse_subgraph("Saki AI architecture", fused_pkg)
    
    assert graph_pkg is not None
    assert graph_pkg.total_nodes >= 1


# -------------------------
# 5. AUTONOMOUS WORKFLOW & RECOVERY TEST
# -------------------------
def test_autonomous_workflow_execution_and_recovery():
    wf = AutonomousWorkflowEngine.create_workflow("Refactor system endpoints")
    telemetry = AutonomousWorkflowEngine.execute_workflow(wf.workflow_id)
    
    assert telemetry.execution_status == "COMPLETED"
    recovered = AutonomousWorkflowEngine.recover_workflows()
    assert isinstance(recovered, list)
