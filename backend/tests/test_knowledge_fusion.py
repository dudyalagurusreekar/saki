import pytest
from backend.services.unified_knowledge import (
    UnifiedKnowledgePackage,
    KnowledgeCandidate,
    SRC_CODE,
    SRC_WEB_SOURCE,
    TRUST_AUTHORITATIVE,
    TRUST_EXTERNAL
)
from backend.services.knowledge_fusion import (
    KnowledgeFusionEngine,
    SUPPORT_SUPPORTED,
    RESOLVED_CONFLICTING
)


# -------------------------
# CLAIM EXTRACTION & FUSION TESTS
# -------------------------
def test_knowledge_fusion_claim_extraction():
    c1 = KnowledgeCandidate(source_type=SRC_CODE, content="FastAPI streaming route handler supported", provenance_label="Verified Workspace Codebase")
    c2 = KnowledgeCandidate(source_type=SRC_WEB_SOURCE, content="FastAPI documentation streaming response example", provenance_label="FastAPI Docs")
    
    rag_pkg = UnifiedKnowledgePackage(candidates=[c1, c2], total_candidates=2)
    fused_pkg = KnowledgeFusionEngine.fuse_knowledge(rag_pkg)
    
    assert fused_pkg.total_claims == 2
    assert fused_pkg.supported_claims_count == 2
    assert fused_pkg.has_conflicts is False


# -------------------------
# CONFLICT DETECTION TEST
# -------------------------
def test_cross_source_conflict_detection():
    c1 = KnowledgeCandidate(source_type=SRC_CODE, content="Saki AI v1 architecture supports local storage", provenance_label="Workspace Code")
    c2 = KnowledgeCandidate(source_type=SRC_WEB_SOURCE, content="Saki AI v2 architecture deprecates local storage", provenance_label="External Web")
    
    rag_pkg = UnifiedKnowledgePackage(candidates=[c1, c2], total_candidates=2)
    fused_pkg = KnowledgeFusionEngine.fuse_knowledge(rag_pkg)
    
    assert fused_pkg.has_conflicts is True
    assert len(fused_pkg.conflicts) > 0
    assert fused_pkg.conflicts[0].resolution_status == RESOLVED_CONFLICTING


# -------------------------
# EMPTY / INSUFFICIENT EVIDENCE TEST
# -------------------------
def test_empty_candidates_fusion():
    rag_pkg = UnifiedKnowledgePackage(candidates=[], total_candidates=0)
    fused_pkg = KnowledgeFusionEngine.fuse_knowledge(rag_pkg)
    
    assert fused_pkg.total_claims == 0
    assert "No candidates" in fused_pkg.details
