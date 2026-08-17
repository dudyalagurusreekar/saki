import pytest
from backend.services.knowledge_graph import (
    KnowledgeGraphEngine,
    KnowledgeNode,
    KnowledgeEdge,
    NT_PROJECT,
    NT_USER,
    NT_GOAL,
    NT_TASK,
    REL_OWNS,
    REL_HAS_TASK,
    STATUS_ACTIVE,
    STATUS_REVOKED
)


# -------------------------
# BASE GRAPH & TRAVERSAL TESTS
# -------------------------
def test_base_graph_initialization():
    KnowledgeGraphEngine.initialize_base_graph()
    pkg = KnowledgeGraphEngine.traverse_subgraph("Saki AI project query")
    
    assert pkg.total_nodes >= 3
    assert pkg.total_edges >= 2
    assert any(n.canonical_id == "project:saki" for n in pkg.nodes)


def test_dynamic_graph_traversal_expansion():
    pkg = KnowledgeGraphEngine.traverse_subgraph("Tell me about browser integration")
    
    assert any(n.canonical_id == "task:browser_integration" for n in pkg.nodes)
    assert any(e.target_node == "task:browser_integration" for e in pkg.edges)
    assert len(pkg.nodes) <= 20
    assert len(pkg.edges) <= 30


# -------------------------
# ENTITY CANONICAL RESOLUTION TEST
# -------------------------
def test_entity_canonical_resolution():
    cid_saki = KnowledgeGraphEngine.resolve_entity_canonical("Saki AI")
    cid_browser = KnowledgeGraphEngine.resolve_entity_canonical("Browser automation")
    
    assert cid_saki == "project:saki"
    assert cid_browser == "task:browser_integration"


# -------------------------
# MEMORY REVOCATION SYNC TEST
# -------------------------
def test_memory_revocation_graph_sync():
    KnowledgeGraphEngine.traverse_subgraph("browser integration")
    KnowledgeGraphEngine.sync_memory_revocation("browser")
    
    pkg = KnowledgeGraphEngine.traverse_subgraph("general query")
    node = next((n for n in pkg.nodes if n.canonical_id == "task:browser_integration"), None)
    
    if node:
        assert node.status == STATUS_REVOKED
