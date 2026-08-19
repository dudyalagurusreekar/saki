"""
Sprint 7 Automated Regression Test Suite: Claim-Level Grounding & Answer Verification
Tests:
- Test 1: Exact supported claim -> SUPPORTED
- Test 2: Unmentioned date claim -> UNSUPPORTED
- Test 3: Compound sentence (supported location + unsupported date) -> first SUPPORTED, second UNSUPPORTED
- Test 4: Conflicting sources (1850 vs 1860) -> CONFLICTED / CONTRADICTED
- Test 5: Official release evidence for software version -> SUPPORTED
- Test 6: General doc lacking version info -> UNSUPPORTED
- Test 7: Food claims verified against culinary evidence
- Test 8: No web evidence for current query -> INSUFFICIENT_EVIDENCE / UNSUPPORTED
- Test 16: Hallucination regression test on restricted evidence
- Test 17: Sentence/clause repair regression test (preserves supported, removes unsupported)
- Test 18: Performance boundary check (< 50ms evaluation)
"""

import time
import pytest
from backend.services.grounding_verifier import (
    GroundingVerifierEngine,
    SupportState,
    Directness,
    ClaimImportance,
    extract_claims_from_text
)
from backend.services.action_engine import ActionDecision, ACTION_WEB_SEARCH, ACTION_LOCAL_REASONING, FRESHNESS_CURRENT, FRESHNESS_STABLE
from backend.services.world_access_manager import EvidenceItem


class TestSprint7ClaimGrounding:

    def test_01_exact_supported_claim(self):
        """
        TEST 1:
        Evidence: 'FastAPI is a Python web framework.'
        Draft: 'FastAPI is a Python web framework.'
        Expected: SUPPORTED
        """
        evidence = [{
            "title": "FastAPI Documentation",
            "content": "FastAPI is a modern, high-performance web framework for building APIs with Python.",
            "url": "https://fastapi.tiangolo.com",
            "domain": "fastapi.tiangolo.com"
        }]
        draft = "FastAPI is a Python web framework."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="what is fastapi"
        )

        assert assessment.total_claims >= 1
        claim = assessment.claims[0]
        assert claim.support_status == SupportState.SUPPORTED.value
        assert claim.directness == Directness.DIRECT_SUPPORT.value
        assert assessment.grounding_status == "FULLY_SUPPORTED"

    def test_02_unmentioned_date_claim(self):
        """
        TEST 2:
        Evidence: 'FastAPI is a Python web framework.'
        Draft: 'FastAPI was created in 2018.'
        Expected: UNSUPPORTED (year 2018 is absent from evidence)
        """
        evidence = [{
            "title": "FastAPI Documentation",
            "content": "FastAPI is a modern, high-performance web framework for building APIs with Python.",
            "url": "https://fastapi.tiangolo.com",
            "domain": "fastapi.tiangolo.com"
        }]
        draft = "FastAPI was created in 2018."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="when was fastapi created"
        )

        assert assessment.total_claims >= 1
        claim = assessment.claims[0]
        assert claim.support_status == SupportState.UNSUPPORTED.value
        assert claim.importance == ClaimImportance.CRITICAL.value
        assert assessment.critical_claims_supported is False

    def test_03_compound_sentence_support_discrimination(self):
        """
        TEST 3:
        Evidence: 'Temple X is located in Vijayawada.'
        Draft: 'Temple X is in Vijayawada and was built in 1500.'
        Expected:
        First claim: SUPPORTED
        Second claim: UNSUPPORTED
        """
        evidence = [{
            "title": "Vijayawada Temples Guide",
            "content": "Temple X is located in Vijayawada on the banks of the river.",
            "url": "https://ap.gov.in/tourism",
            "domain": "ap.gov.in"
        }]
        draft = "Temple X is in Vijayawada and was built in 1500."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="tell me about Temple X"
        )

        assert len(assessment.claims) == 2
        claim_loc = assessment.claims[0]
        claim_date = assessment.claims[1]

        assert "Vijayawada" in claim_loc.text
        assert claim_loc.support_status == SupportState.SUPPORTED.value

        assert "1500" in claim_date.text
        assert claim_date.support_status == SupportState.UNSUPPORTED.value

    def test_04_conflicting_sources_contradiction_detection(self):
        """
        TEST 4:
        Source A: 'Founded in 1850.'
        Source B: 'Founded in 1860.'
        Draft: 'The organization was founded in 1850.'
        Expected: CONFLICTED / CONTRADICTED
        """
        evidence = [
            {
                "title": "Source A Historical Archive",
                "content": "The institution was founded in 1850 during the early colonial administrative era.",
                "url": "https://source-a.org",
                "domain": "source-a.org"
            },
            {
                "title": "Source B Gazetteer Record",
                "content": "Official municipal records state it was founded in 1860 following regional consolidation.",
                "url": "https://source-b.org",
                "domain": "source-b.org"
            }
        ]
        draft = "The institution was founded in 1850."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="when was the institution founded"
        )

        assert assessment.contradicted_claims >= 1
        claim = assessment.claims[0]
        assert claim.support_status == SupportState.CONTRADICTED.value
        assert claim.contradiction_status == "CONFLICTED"
        assert "disagree" in claim.reason.lower()

    def test_05_software_version_official_source_supported(self):
        """
        TEST 5:
        Query: 'latest FastAPI version'
        Evidence: Official release notes say 'FastAPI 0.115.0 was released with Pydantic v2 support.'
        Draft: 'The latest version of FastAPI is 0.115.0.'
        Expected: SUPPORTED
        """
        evidence = [{
            "title": "FastAPI Release 0.115.0 - GitHub",
            "content": "Release notes: FastAPI 0.115.0 was released with enhanced dependency injection and Pydantic v2 compatibility.",
            "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
            "domain": "github.com"
        }]
        draft = "The latest version of FastAPI is 0.115.0."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, freshness_requirement=FRESHNESS_CURRENT, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="latest FastAPI version"
        )

        assert assessment.total_claims >= 1
        claim = assessment.claims[0]
        assert claim.support_status == SupportState.SUPPORTED.value
        assert claim.directness == Directness.DIRECT_SUPPORT.value
        assert assessment.critical_claims_supported is True

    def test_06_software_version_generic_doc_unsupported(self):
        """
        TEST 6:
        Query: 'latest FastAPI version'
        Evidence: General tutorial without version numbers.
        Draft: 'The latest version of FastAPI is 0.115.0.'
        Expected: UNSUPPORTED (0.115.0 is not in evidence)
        """
        evidence = [{
            "title": "FastAPI Overview",
            "content": "FastAPI is a modern web framework for Python. It allows building high performance APIs quickly.",
            "url": "https://fastapi.tiangolo.com/tutorial",
            "domain": "fastapi.tiangolo.com"
        }]
        draft = "The latest version of FastAPI is 0.115.0."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, freshness_requirement=FRESHNESS_CURRENT, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="latest FastAPI version"
        )

        assert assessment.total_claims >= 1
        claim = assessment.claims[0]
        assert claim.support_status == SupportState.UNSUPPORTED.value
        assert assessment.critical_claims_supported is False

    def test_07_food_in_vijayawada_claim_support(self):
        """
        TEST 7:
        Query: 'special food in Vijayawada'
        Evidence: discusses punugulu and gongura pachadi.
        Draft A: 'Vijayawada is famous for punugulu and gongura pachadi.' -> SUPPORTED
        Draft B: 'Vijayawada is famous for authentic sushi.' -> UNSUPPORTED
        """
        evidence = [{
            "title": "Vijayawada Food Specialties",
            "content": "Vijayawada is famous for traditional street snacks like punugulu, spicy gongura pachadi, and Andhra meals.",
            "url": "https://food.andhra.gov.in",
            "domain": "food.andhra.gov.in"
        }]
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        draft_a = "Vijayawada is famous for punugulu and gongura pachadi."
        assessment_a = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft_a,
            evidence_items=evidence,
            action_decision=action,
            user_query="special food in Vijayawada"
        )
        assert assessment_a.supported_claims >= 1

        draft_b = "Vijayawada is famous for authentic sushi."
        assessment_b = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft_b,
            evidence_items=evidence,
            action_decision=action,
            user_query="special food in Vijayawada"
        )
        assert assessment_b.unsupported_claims >= 1

    def test_08_no_web_evidence_for_current_query(self):
        """
        TEST 8:
        No web evidence retrieved (rate limit / failure).
        Draft contains current factual claim: 'FastAPI version is 0.115.0.'
        Expected: UNSUPPORTED / INSUFFICIENT_EVIDENCE
        """
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, freshness_requirement=FRESHNESS_CURRENT, reason="test", confidence=1.0)
        draft = "FastAPI latest version is 0.115.0."

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=[],
            action_decision=action,
            user_query="latest FastAPI version"
        )

        assert assessment.grounding_status == "INSUFFICIENT_EVIDENCE"
        assert assessment.unsupported_claims >= 1
        assert assessment.critical_claims_supported is False

    def test_16_hallucination_regression_on_restricted_evidence(self):
        """
        TEST 16: Hallucination Regression Test
        Restricted Evidence: 'Temple X is located in Vijayawada.'
        Draft contains ungrounded facts: 'Temple X was built in the 15th century by King Y beside the Krishna River.'
        Expected: Detects all ungrounded historical claims as UNSUPPORTED.
        """
        evidence = [{
            "title": "Vijayawada Temple List",
            "content": "Temple X is located in Vijayawada.",
            "url": "https://ap.gov.in",
            "domain": "ap.gov.in"
        }]
        draft = "Temple X was built in the 15th century by King Y beside the Krishna River."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="tell me about Temple X"
        )

        assert assessment.unsupported_claims >= 1
        assert assessment.critical_claims_supported is False

    def test_17_answer_repair_removes_unsupported_facts(self):
        """
        TEST 17: Answer Repair Regression Test
        Input Evidence: 'Temple X is located in Vijayawada.'
        Draft: 'Temple X is located in Vijayawada and was built in 1500.'
        Expected Final Repaired Text: 'Temple X is located in Vijayawada.'
        (Removes the unsupported date without fabricating a new date).
        """
        evidence = [{
            "title": "Vijayawada Temple List",
            "content": "Temple X is located in Vijayawada.",
            "url": "https://ap.gov.in",
            "domain": "ap.gov.in"
        }]
        draft = "Temple X is located in Vijayawada and was built in 1500."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="tell me about Temple X"
        )

        repaired = assessment.repaired_answer
        assert "Vijayawada" in repaired
        assert "1500" not in repaired

    def test_18_grounding_evaluation_performance(self):
        """
        TEST 18: Performance Requirement
        Grounding evaluation must execute in bounded time (< 50ms).
        """
        evidence = [{
            "title": "FastAPI Docs",
            "content": "FastAPI is a Python web framework with high performance.",
            "url": "https://fastapi.tiangolo.com",
            "domain": "fastapi.tiangolo.com"
        }]
        draft = "FastAPI is a Python web framework. It supports async operations and automatic docs."
        action = ActionDecision(action=ACTION_WEB_SEARCH, requires_world_access=True, reason="test", confidence=1.0)

        t0 = time.time()
        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_items=evidence,
            action_decision=action,
            user_query="what is fastapi"
        )
        elapsed_ms = (time.time() - t0) * 1000

        assert elapsed_ms < 50.0
        assert assessment.verification_latency_ms < 50.0
