"""
Unit and Integration Tests for Claim Verification Workflows
"""

import pytest
from backend.services.evidence_engine import EvidenceIntelligenceEngine


def test_explicit_verification_request_intent():
    """Verify that explicit verification query patterns set intent to verification."""
    from backend.services.action_engine import decide_action
    query = "Verify whether Kambadur Temple is dedicated to Siva."
    decision = decide_action(query)
    assert decision.query_intent == "verification"


def test_multi_source_conflict_comparison():
    """Verify that conflicting claims from different sources are correctly flagged as CONFLICT in verification mode."""
    query = "Does the government support Kambadur Temple heritage?"
    raw_items = [
        {
            "title": "Government District Portal",
            "snippet": "The government supports that Kambadur Temple is a heritage site.",
            "url": "https://gov.in/heritage"
        },
        {
            "title": "A random blog",
            "snippet": "The government does not support that Kambadur Temple is a heritage site.",
            "url": "https://blog.com/kambadur"
        }
    ]
    
    package = EvidenceIntelligenceEngine.process_and_synthesize(
        query=query,
        raw_items=raw_items,
        is_verification_mode=True
    )
    
    assert len(package.conflicts) > 0
    conflict_claims = [c for c in package.claims if c.support_status == "CONFLICT"]
    assert len(conflict_claims) > 0


def test_verified_vs_unsupported_claims():
    """Verify that consistent, non-conflicting claims are marked VERIFIED in verification mode."""
    query = "What century was Kambadur Temple built?"
    raw_items = [
        {
            "title": "Archeological Survey of India",
            "snippet": "Malleswara Swamy Temple at Kambadur was built in the 8th century.",
            "url": "https://gov.in/asi"
        }
    ]
    
    package = EvidenceIntelligenceEngine.process_and_synthesize(
        query=query,
        raw_items=raw_items,
        is_verification_mode=True
    )
    
    assert len(package.claims) > 0
    assert package.claims[0].support_status == "VERIFIED"
