"""
Sprint 9 Automated Regression Test Suite: Source Trust, Freshness & Conflict Resolution
Covers Tests 1-12 required by Sprint 9 specifications.
"""

import pytest
from backend.services.source_trust_engine import (
    SourceTrustClassifier,
    FreshnessEvaluator,
    ConflictResolutionEngine,
    EvidenceSelector,
    AuthorityLevel,
    SourceCategory,
    FreshnessLevel,
    ReliabilityStatus
)
from backend.services.grounding_verifier import GroundingVerifierEngine, GroundingClaim, extract_claims_from_text


class TestSprint9SourceTrustAndFreshness:
    """Automated test suite for Sprint 9 source assessment, freshness, and conflict resolution."""

    def test_01_primary_source_preferred_over_random_blog(self):
        """TEST 1: Primary source vs random blog. Expected: primary source preferred."""
        query = "latest FastAPI version"
        raw_items = [
            {
                "url": "https://randomtechblog123.blogspot.com/post/fastapi",
                "domain": "randomtechblog123.blogspot.com",
                "snippet": "FastAPI is a modern web framework for Python.",
                "relevance_score": 0.85
            },
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
                "domain": "github.com",
                "snippet": "Release FastAPI 0.115.0 with full Pydantic v2 support. Released in 2026.",
                "relevance_score": 0.95
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="FastAPI"
        )

        assert len(result.selected_evidence) >= 1
        top_source = result.selected_evidence[0]
        assert "github.com" in top_source.domain
        assert top_source.authority_level == AuthorityLevel.PRIMARY.value
        assert top_source.composite_selection_score > result.selected_evidence[-1].composite_selection_score or len(result.selected_evidence) == 1

    def test_02_current_primary_preferred_over_stale_primary(self):
        """TEST 2: Current primary source vs stale primary source. Expected: current source preferred for current query."""
        query = "latest FastAPI version"
        raw_items = [
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.100.0",
                "domain": "github.com",
                "snippet": "FastAPI 0.100.0 released in 2023.",
                "relevance_score": 0.85
            },
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
                "domain": "github.com",
                "snippet": "FastAPI 0.115.0 released in 2026.",
                "relevance_score": 0.95
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="FastAPI"
        )

        top_source = result.selected_evidence[0]
        assert top_source.published_year == 2026
        assert top_source.freshness_status == FreshnessLevel.CURRENT.value

    def test_03_current_primary_preferred_over_current_secondary(self):
        """TEST 3: Current secondary source vs current primary source. Expected: primary source preferred."""
        query = "latest Python version"
        raw_items = [
            {
                "url": "https://realpython.com/python-news-2026",
                "domain": "realpython.com",
                "snippet": "Python 3.14 was released in 2026.",
                "relevance_score": 0.90
            },
            {
                "url": "https://python.org/downloads/release/python-3140",
                "domain": "python.org",
                "snippet": "Python 3.14.0 release notes from Python Software Foundation in 2026.",
                "relevance_score": 0.95
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="Python"
        )

        top_source = result.selected_evidence[0]
        assert "python.org" in top_source.domain
        assert top_source.authority_level == AuthorityLevel.PRIMARY.value

    def test_04_two_independent_sources_agree_multi_source_supported(self):
        """TEST 4: Two independent sources agree. Expected: MULTI_SOURCE_SUPPORTED."""
        query = "special food in Vijayawada"
        raw_items = [
            {
                "url": "https://tourism.ap.gov.in/culinary/vijayawada",
                "domain": "tourism.ap.gov.in",
                "snippet": "Vijayawada is famous for Gongura pachadi and Punugulu street food.",
                "relevance_score": 0.95
            },
            {
                "url": "https://thehindu.com/life-and-style/food/vijayawada-delicacies",
                "domain": "thehindu.com",
                "snippet": "Gongura pachadi and Punugulu are iconic street foods in Vijayawada.",
                "relevance_score": 0.90
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="Vijayawada"
        )

        assert result.overall_status == "MULTI_SOURCE_SUPPORTED"
        assert result.diversity_count == 2

    def test_05_two_sources_disagree_conflicted_detected(self):
        """TEST 5: Two sources disagree on founding date without primary resolution. Expected: CONFLICTED."""
        query = "when was the monument built"
        raw_items = [
            {
                "url": "https://heritageblog1.com/monument",
                "domain": "heritageblog1.com",
                "snippet": "The ancient monument was founded in 1850.",
                "relevance_score": 0.85
            },
            {
                "url": "https://heritageblog2.com/monument",
                "domain": "heritageblog2.com",
                "snippet": "Official records state the monument was founded in 1860.",
                "relevance_score": 0.85
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="STABLE"
        )

        assert result.overall_status == "CONFLICTED"
        assert len(result.conflicts_detected) >= 1
        assert result.conflicts_detected[0].conflict_type == "CHRONOLOGICAL_CONFLICT"

    def test_06_duplicate_url_counted_once(self):
        """TEST 6: Duplicate URL. Expected: counted once."""
        query = "latest FastAPI version"
        raw_items = [
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0?utm_source=google",
                "domain": "github.com",
                "snippet": "Release FastAPI 0.115.0 in 2026.",
                "relevance_score": 0.95
            },
            {
                "url": "https://github.com/tiangolo/fastapi/releases/tag/0.115.0",
                "domain": "github.com",
                "snippet": "Release FastAPI 0.115.0 in 2026.",
                "relevance_score": 0.95
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT"
        )

        assert len(result.selected_evidence) == 1
        assert result.diversity_count == 1

    def test_07_same_domain_copied_results_not_treated_as_independent(self):
        """TEST 7: Same-domain copied results. Expected: not treated as independent confirmation."""
        query = "special food in Vijayawada"
        raw_items = [
            {
                "url": "https://foodblog.com/page1",
                "domain": "foodblog.com",
                "snippet": "Punugulu is a great snack in Vijayawada.",
                "relevance_score": 0.80
            },
            {
                "url": "https://foodblog.com/page2",
                "domain": "foodblog.com",
                "snippet": "Punugulu is an awesome food in Vijayawada.",
                "relevance_score": 0.80
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT"
        )

        assert result.diversity_count == 1
        assert result.overall_status != "MULTI_SOURCE_SUPPORTED"

    def test_08_current_query_with_stale_evidence_triggers_stale_warning(self):
        """TEST 8: Current query + stale evidence. Expected: STALE_EVIDENCE."""
        query = "latest FastAPI version"
        raw_items = [
            {
                "url": "https://fastapi.tiangolo.com/history/2023",
                "domain": "fastapi.tiangolo.com",
                "snippet": "FastAPI version 0.95.0 was released in 2023.",
                "relevance_score": 0.75
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT",
            target_entity="FastAPI"
        )

        assert result.overall_status == "STALE_EVIDENCE"
        assert result.selected_evidence[0].freshness_status == FreshnessLevel.STALE.value

    def test_09_historical_query_with_old_authoritative_evidence_remains_valid(self):
        """TEST 9: Historical query + old authoritative evidence. Expected: old evidence remains valid."""
        query = "who built the Eiffel Tower"
        raw_items = [
            {
                "url": "https://toureiffel.paris/en/history",
                "domain": "toureiffel.paris",
                "snippet": "The Eiffel Tower was built by Gustave Eiffel for the 1889 Exposition Universelle in Paris.",
                "relevance_score": 0.95
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="STABLE"
        )

        assert result.overall_status == "SUFFICIENT"
        assert result.selected_evidence[0].freshness_status == FreshnessLevel.CURRENT.value

    def test_10_restaurant_source_claims_its_own_menu_strong_support(self):
        """TEST 10: Restaurant source claims its own menu. Expected: strong support for menu claim."""
        query = "what does Minerva Grand restaurant serve in Vijayawada"
        claim_text = "Minerva Grand restaurant serves South Indian thali and filter coffee."
        evidence_list = [
            {
                "url": "https://minervagrandrestaurant.com/menu",
                "domain": "minervagrandrestaurant.com",
                "content": "Minerva Grand restaurant serves South Indian thali, dosa, and filter coffee."
            }
        ]

        claim_res = GroundingVerifierEngine.verify_claim_against_evidence(claim_text, evidence_list)
        assert claim_res["support_status"] == "SUPPORTED"
        assert claim_res["directness"] == "DIRECT_SUPPORT"

    def test_11_restaurant_source_claims_best_restaurant_in_city_weak_support(self):
        """TEST 11: Restaurant source claims 'best restaurant in Vijayawada'. Expected: weak/unsupported."""
        query = "what is the best restaurant in Vijayawada"
        claim_text = "Minerva Grand restaurant is the best restaurant in Vijayawada."
        evidence_list = [
            {
                "url": "https://minervagrandrestaurant.com/about",
                "domain": "minervagrandrestaurant.com",
                "content": "Minerva Grand restaurant is the best restaurant in Vijayawada with exceptional food."
            }
        ]

        claim_res = GroundingVerifierEngine.verify_claim_against_evidence(claim_text, evidence_list)
        assert claim_res["support_status"] in ["PARTIALLY_SUPPORTED", "UNSUPPORTED"]
        assert claim_res["directness"] == "INSUFFICIENT"
        assert "Self-asserted superlative" in claim_res["reason"]

    def test_12_no_trustworthy_evidence_insufficient_trustworthy_evidence(self):
        """TEST 12: No trustworthy evidence (all unknown, low relevance). Expected: INSUFFICIENT_TRUSTWORTHY_EVIDENCE."""
        query = "obscure query with no good results"
        raw_items = [
            {
                "url": "https://randomspamblog.xyz/post",
                "domain": "randomspamblog.xyz",
                "snippet": "Unrelated generic text.",
                "relevance_score": 0.20
            }
        ]

        result = EvidenceSelector.select_best_evidence(
            raw_items=raw_items,
            query=query,
            temporal_requirement="CURRENT"
        )

        assert result.overall_status == "INSUFFICIENT_TRUSTWORTHY_EVIDENCE"
        assert len(result.selected_evidence) == 0
