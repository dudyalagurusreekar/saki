"""
Sprint 10 Final Intelligence Integration & Production Hardening Benchmark Suite
Validates the complete end-to-end Saki pipeline from User Query to Grounded Final Answer.
"""

import time
import pytest
from backend.services.action_engine import parse_query_understanding, decide_action
from backend.services.evidence_engine import EvidenceIntelligenceEngine, RelevanceGate
from backend.services.source_trust_engine import EvidenceSelector, AuthorityLevel, FreshnessLevel
from backend.services.grounding_verifier import GroundingVerifierEngine, extract_claims_from_text, GroundingClaim
from backend.routes.chat import ChatRequest, chat


class TestSprint10FinalIntelligenceIntegration:
    """Complete End-to-End Reliability Benchmark for Saki Production Pipeline."""

    def test_01_static_knowledge_pipeline_e2e(self):
        """Validates static general knowledge path: No web access triggered, clean model explanation."""
        query = "what is FastAPI"
        qu = parse_query_understanding(query)
        decision = decide_action(query)

        assert decision.requires_world_access is False
        assert decision.freshness_requirement in ["STABLE", "NONE", "LOW"]

        # Run Grounding assessment on static answer
        static_draft = "FastAPI is a modern, fast, web framework for building APIs with Python 3.8+ based on standard Python type hints."
        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=static_draft,
            evidence_package=None,
            action_decision=decision,
            user_query=query
        )

        assert assessment.answer_source_mode == "STATIC_KNOWLEDGE"
        assert assessment.grounding_status == "FULLY_SUPPORTED"
        assert len(assessment.repaired_answer) > 20

    def test_02_current_information_web_pipeline_e2e(self):
        """Validates current information path: Web required, search query optimized, evidence synthesized, claim grounded."""
        query = "latest FastAPI version"
        qu = parse_query_understanding(query)
        decision = decide_action(query)

        assert decision.requires_world_access is True
        assert decision.freshness_requirement == "CURRENT"
        assert qu.primary_entity == "FastAPI"

        raw_items = [
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
                "domain": "github.com",
                "snippet": "FastAPI version 0.115.0 was released in 2026 with full Pydantic v2 support.",
                "relevance_score": 0.98
            }
        ]

        # Process evidence through unified engine
        evidence_pkg = EvidenceIntelligenceEngine.process_and_synthesize(
            query=query,
            raw_items=raw_items,
            freshness_requirement=decision.freshness_requirement
        )

        assert len(evidence_pkg.evidence_items) >= 1
        assert evidence_pkg.evidence_status in ["SUFFICIENT", "MULTI_SOURCE_SUPPORTED"]

        # Ground draft response
        draft = "The latest version of FastAPI is 0.115.0, released in 2026."
        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft,
            evidence_package=evidence_pkg,
            action_decision=decision,
            user_query=query
        )

        assert assessment.grounding_status == "FULLY_SUPPORTED"
        assert assessment.supported_claims >= 1
        assert assessment.unsupported_claims == 0

    def test_03_entity_and_semantic_relevance_e2e(self):
        """Validates RelevanceGate discrimination: Culinary content accepted, tourism history rejected."""
        query = "special food in Vijayawada"
        qu = parse_query_understanding(query)

        raw_items = [
            {
                "url": "https://ap.gov.in/food",
                "domain": "ap.gov.in",
                "snippet": "Famous Vijayawada dishes include spicy Gongura pachadi, Punugulu, and Andhra meals.",
                "title": "Culinary Heritage"
            },
            {
                "url": "https://weather.com/vijayawada",
                "domain": "weather.com",
                "snippet": "Today's weather in Vijayawada is sunny with a high of 34C.",
                "title": "Vijayawada Weather Forecast"
            }
        ]

        evaluations = RelevanceGate.evaluate_relevance(query, raw_items)
        assert evaluations[0] == "RELEVANT"
        assert evaluations[1] == "IRRELEVANT"

    def test_04_source_trust_priority_e2e(self):
        """Validates SourceTrustClassifier and EvidenceSelector: Primary official documentation beats third-party blog."""
        query = "latest Python version"
        raw_items = [
            {
                "url": "https://someunverifiedblog.net/post/python-version",
                "domain": "someunverifiedblog.net",
                "snippet": "Python 3.14 was released.",
                "relevance_score": 0.80
            },
            {
                "url": "https://python.org/downloads/release/python-3140",
                "domain": "python.org",
                "snippet": "Official release notes: Python 3.14.0 released in 2026.",
                "relevance_score": 0.95
            }
        ]

        selection = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="Python"
        )

        top_source = selection.selected_evidence[0]
        assert "python.org" in top_source.domain
        assert top_source.authority_level == AuthorityLevel.PRIMARY.value

    def test_05_query_dependent_freshness_e2e(self):
        """Validates FreshnessEvaluator: 2026 data is CURRENT; 2023 data is STALE for temporal query."""
        query = "latest FastAPI version"
        stale_items = [
            {
                "url": "https://fastapi.tiangolo.com/history/2023",
                "domain": "fastapi.tiangolo.com",
                "snippet": "FastAPI version 0.95.0 was released in 2023.",
                "relevance_score": 0.85
            }
        ]

        selection = EvidenceSelector.select_best_evidence(
            raw_items=stale_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="FastAPI"
        )

        assert selection.overall_status == "STALE_EVIDENCE"
        assert selection.selected_evidence[0].freshness_status == FreshnessLevel.STALE.value

    def test_06_multi_source_agreement_e2e(self):
        """Validates Multi-Source Corroboration: 2 independent domains agree -> MULTI_SOURCE_SUPPORTED."""
        query = "special food in Vijayawada"
        raw_items = [
            {
                "url": "https://tourism.ap.gov.in/food",
                "domain": "tourism.ap.gov.in",
                "snippet": "Vijayawada is famous for Gongura pachadi and Punugulu street food.",
                "relevance_score": 0.95
            },
            {
                "url": "https://thehindu.com/vijayawada-food",
                "domain": "thehindu.com",
                "snippet": "Gongura pachadi and Punugulu are iconic street foods in Vijayawada.",
                "relevance_score": 0.90
            }
        ]

        selection = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT"
        )

        assert selection.overall_status == "MULTI_SOURCE_SUPPORTED"
        assert selection.diversity_count == 2

    def test_07_conflict_detection_and_qualification_e2e(self):
        """Validates Conflict Resolution: Unresolved chronological discrepancy -> CONFLICTED."""
        query = "when was the historic temple built"
        raw_items = [
            {
                "url": "https://heritage1.org/temple",
                "domain": "heritage1.org",
                "snippet": "The temple was founded in 1850.",
                "relevance_score": 0.85
            },
            {
                "url": "https://heritage2.org/temple",
                "domain": "heritage2.org",
                "snippet": "Historical records show the temple was founded in 1860.",
                "relevance_score": 0.85
            }
        ]

        selection = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="STABLE"
        )

        assert selection.overall_status == "CONFLICTED"
        assert len(selection.conflicts_detected) >= 1

    def test_08_claim_level_grounding_and_repair_e2e(self):
        """Validates GroundingVerifierEngine: Unsupported critical clause stripped while supported clause is retained."""
        query = "tell me about Temple X in Vijayawada"
        decision = decide_action(query)

        evidence_items = [
            {
                "url": "https://kanakadurgamma.org/history",
                "domain": "kanakadurgamma.org",
                "content": "Temple X is located on the Indrakeeladri hill in Vijayawada on the banks of the Krishna River."
            }
        ]

        draft_response = "Temple X is located on the Indrakeeladri hill in Vijayawada and was built in 1500 by King Y."

        assessment = GroundingVerifierEngine.evaluate_answer_grounding(
            draft_text=draft_response,
            evidence_package=None,
            action_decision=decision,
            user_query=query
        )

        # Re-evaluate with explicit evidence list
        claims = extract_claims_from_text(draft_response)
        evaluated_claims = []
        for c in claims:
            res = GroundingVerifierEngine.verify_claim_against_evidence(c, evidence_items)
            c.support_status = res["support_status"]
            c.directness = res["directness"]
            c.importance = "CRITICAL" if "1500" in c.text or "king" in c.text.lower() else "NORMAL"
            evaluated_claims.append(c)

        repaired = GroundingVerifierEngine.repair_answer_grounding(
            draft_text=draft_response,
            claims=evaluated_claims,
            contradictions=[],
            source_mode="WEB_GROUNDED"
        )

        assert "Temple X is located on the Indrakeeladri hill in Vijayawada" in repaired
        assert "1500" not in repaired
        assert "King Y" not in repaired

    def test_09_fail_closed_on_provider_error_e2e(self):
        """Validates Fail-Closed Safety: External provider rate limit or error produces controlled limitation response."""
        query = "latest FastAPI version"
        raw_items = [
            {
                "url": "",
                "domain": "",
                "snippet": "",
                "provider": "gemini",
                "provider_status": "FAILURE",
                "error_detail": "HTTP_429"
            }
        ]

        evidence_pkg = EvidenceIntelligenceEngine.process_and_synthesize(
            query=query,
            raw_items=raw_items,
            freshness_requirement="CURRENT"
        )

        assert evidence_pkg.evidence_status == "INSUFFICIENT"
        assert all(ev.process_state == "IRRELEVANT" for ev in evidence_pkg.evidence_items)
        assert len(evidence_pkg.claims) == 0

    def test_10_pipeline_performance_bounds_e2e(self):
        """Validates Performance Bounds: Grounding, relevance, and source assessment complete in < 50ms."""
        query = "latest FastAPI version"
        raw_items = [
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
                "domain": "github.com",
                "snippet": "FastAPI version 0.115.0 released in 2026.",
                "relevance_score": 0.95
            },
            {
                "url": "https://pypi.org/project/fastapi",
                "domain": "pypi.org",
                "snippet": "FastAPI 0.115.0 package on PyPI.",
                "relevance_score": 0.90
            }
        ]

        t0 = time.time()
        # 1. Relevance Gate
        rel_evals = RelevanceGate.evaluate_relevance(query, raw_items)
        # 2. Source Trust & Selection
        selection = EvidenceSelector.select_best_evidence(raw_items, query, "CURRENT", "FastAPI")
        # 3. Grounding Verification
        draft = "FastAPI 0.115.0 is the latest version."
        claims = extract_claims_from_text(draft)
        for c in claims:
            GroundingVerifierEngine.verify_claim_against_evidence(c, raw_items)
        elapsed_ms = (time.time() - t0) * 1000

        assert elapsed_ms < 50.0  # Must be well under 50ms
