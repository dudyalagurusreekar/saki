import pytest
from backend.services.evidence_engine import (
    URLCanonicalizer,
    DeduplicationEngine,
    SourceAuthorityAnalyzer,
    ConflictDetector,
    EvidenceIntelligenceEngine,
    SourceModel,
    ClaimModel,
    EvidencePackage,
    SOURCE_TECHNICAL_DOCUMENTATION,
    PRIMARY_SOURCE,
    AUTHORITY_HIGH,
    AUTHORITY_LOW,
    CONFLICT_DIRECT,
    CONFLICT_TEMPORAL,
    EVIDENCE_STATUS_SUFFICIENT,
    EVIDENCE_STATUS_INSUFFICIENT
)


# -------------------------
# URL CANONICALIZATION TESTS
# -------------------------
def test_url_canonicalizer_strips_tracking_params():
    raw_url = "https://docs.python.org/3/whatsnew/3.12.html?utm_source=newsletter&utm_medium=email&article=42#section1"
    canon = URLCanonicalizer.canonicalize(raw_url)
    
    assert "utm_source" not in canon
    assert "utm_medium" not in canon
    assert "article=42" in canon  # Content query parameter preserved
    assert canon.startswith("https://docs.python.org/3/whatsnew/3.12.html")


def test_url_canonicalizer_normalizes_casing_and_ports():
    raw_url = "HTTP://DOCS.PYTHON.ORG:80/3/index.html/"
    canon = URLCanonicalizer.canonicalize(raw_url)
    assert canon == "http://docs.python.org/3/index.html"


# -------------------------
# DEDUPLICATION & DIVERSITY TESTS
# -------------------------
def test_deduplication_engine_removes_exact_and_content_duplicates():
    raw_items = [
        {"title": "Python 3.12", "snippet": "Python 3.12 introduces new features.", "url": "https://python.org/3.12"},
        {"title": "Python 3.12 Copy", "snippet": "Python 3.12 introduces new features.", "url": "https://mirror.python.org/3.12"}, # Duplicate content
        {"title": "Python 3.12", "snippet": "Python 3.12 introduces new features.", "url": "https://python.org/3.12?utm_source=test"}, # Canonical URL duplicate
        {"title": "FastAPI Guide", "snippet": "FastAPI is a fast web framework.", "url": "https://fastapi.tiangolo.com/"}
    ]
    unique_items, diversity = DeduplicationEngine.deduplicate(raw_items)
    
    assert len(unique_items) == 2
    assert diversity["unique_domains"] == 2
    assert diversity["duplicate_groups_removed"] == 2


# -------------------------
# SOURCE AUTHORITY TESTS
# -------------------------
def test_source_authority_official_docs():
    s_type, is_primary, authority = SourceAuthorityAnalyzer.analyze_source("https://docs.python.org/3/", "docs.python.org")
    assert s_type == SOURCE_TECHNICAL_DOCUMENTATION
    assert is_primary == PRIMARY_SOURCE
    assert authority == AUTHORITY_HIGH


def test_source_authority_community_forum():
    s_type, is_primary, authority = SourceAuthorityAnalyzer.analyze_source("https://reddit.com/r/python", "reddit.com")
    assert authority == AUTHORITY_LOW


# -------------------------
# CONFLICT DETECTION TESTS
# -------------------------
def test_conflict_detector_direct_conflict():
    src1 = SourceModel(source_id="src-1", domain="a.com", url="http://a.com", title="A", canonical_url="http://a.com")
    src2 = SourceModel(source_id="src-2", domain="b.com", url="http://b.com", title="B", canonical_url="http://b.com")
    
    claims = [
        ClaimModel(claim_id="c1", text="Version 2.0 supports CUDA 12", source_ids=["src-1"]),
        ClaimModel(claim_id="c2", text="Version 2.0 does not support CUDA 12", source_ids=["src-2"])
    ]
    
    conflicts = ConflictDetector.evaluate_conflicts(claims, [src1, src2])
    assert len(conflicts) == 1
    assert conflicts[0].category in [CONFLICT_DIRECT, CONFLICT_TEMPORAL]


def test_conflict_detector_temporal_conflict():
    src1 = SourceModel(source_id="src-1", domain="a.com", url="http://a.com", title="A", canonical_url="http://a.com", published_at=1700000000)
    src2 = SourceModel(source_id="src-2", domain="b.com", url="http://b.com", title="B", canonical_url="http://b.com", published_at=1730000000) # 6 months newer
    
    claims = [
        ClaimModel(claim_id="c1", text="Library supports Python 3.10", source_ids=["src-1"]),
        ClaimModel(claim_id="c2", text="Library does not support Python 3.10", source_ids=["src-2"])
    ]
    
    conflicts = ConflictDetector.evaluate_conflicts(claims, [src1, src2])
    assert len(conflicts) == 1
    assert conflicts[0].category == CONFLICT_TEMPORAL


# -------------------------
# EVIDENCE PACKAGE & PROMPT BLOCK TESTS
# -------------------------
def test_evidence_synthesis_and_grounded_prompt_block():
    raw_items = [
        {"title": "Python 3.12 Features", "snippet": "Python 3.12 improves F-strings and performance.", "url": "https://docs.python.org/3/whatsnew/3.12.html"},
        {"title": "FastAPI Release", "snippet": "FastAPI provides high performance async endpoints.", "url": "https://fastapi.tiangolo.com/"}
    ]
    
    package = EvidenceIntelligenceEngine.process_and_synthesize("Python 3.12 features", raw_items)
    assert isinstance(package, EvidencePackage)
    assert package.evidence_status == EVIDENCE_STATUS_SUFFICIENT
    assert len(package.sources) == 2
    
    grounded_block = EvidenceIntelligenceEngine.format_grounded_prompt_block(package)
    assert "<external_web_content>" in grounded_block
    assert "--- [Source 1] ---" in grounded_block
    assert "Title: Python 3.12 Features" in grounded_block
    assert "URL: https://docs.python.org/3/whatsnew/3.12.html" in grounded_block


def test_insufficient_evidence_handling():
    package = EvidenceIntelligenceEngine.process_and_synthesize("Unknown topic", [])
    assert package.evidence_status == EVIDENCE_STATUS_INSUFFICIENT
    assert len(package.sources) == 0
    
    grounded_block = EvidenceIntelligenceEngine.format_grounded_prompt_block(package)
    assert "Note: Insufficient external evidence" in grounded_block
