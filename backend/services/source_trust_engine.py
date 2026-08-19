"""
Saki Source Trust, Freshness & Conflict Resolution Subsystem (Sprint 9)
Evaluates source authority, category, query-dependent freshness, claim-dependent trust,
source independence, multi-source agreement, and conflict resolution.
"""

import re
import time
import urllib.parse
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from backend.services.evidence_engine import URLCanonicalizer, DeduplicationEngine


# -------------------------
# ENUMS & CONSTANTS
# -------------------------
CURRENT_OPERATING_YEAR = 2026

class AuthorityLevel(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"
    UNKNOWN = "UNKNOWN"

class SourceCategory(str, Enum):
    OFFICIAL_DOCS = "OFFICIAL_DOCS"
    OFFICIAL_RELEASE = "OFFICIAL_RELEASE"
    GOVERNMENT = "GOVERNMENT"
    OFFICIAL_COMPANY = "OFFICIAL_COMPANY"
    LOCAL_BUSINESS = "LOCAL_BUSINESS"
    ESTABLISHED_NEWS = "ESTABLISHED_NEWS"
    TECH_PUBLICATION = "TECH_PUBLICATION"
    INDEPENDENT_DB = "INDEPENDENT_DB"
    BLOG = "BLOG"
    COMMUNITY = "COMMUNITY"
    UNKNOWN = "UNKNOWN"

class FreshnessLevel(str, Enum):
    CURRENT = "CURRENT"
    RECENT = "RECENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"

class ReliabilityStatus(str, Enum):
    TRUSTED = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"

class DuplicateStatus(str, Enum):
    UNIQUE = "UNIQUE"
    DUPLICATE_URL = "DUPLICATE_URL"
    DUPLICATE_CONTENT = "DUPLICATE_CONTENT"
    SAME_DOMAIN_COPY = "SAME_DOMAIN_COPY"

class IndependenceStatus(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    SYNDICATED = "SYNDICATED"
    MIRROR = "MIRROR"
    SAME_NETWORK = "SAME_NETWORK"


# Known High-Reputation Registries & Domains
ESTABLISHED_NEWS_DOMAINS = {
    "reuters.com", "bbc.com", "apnews.com", "thehindu.com", 
    "indianexpress.com", "timesofindia.indiatimes.com", "ndtv.com",
    "bloomberg.com", "wsj.com", "nytimes.com", "techcrunch.com", "theverge.com"
}

TECH_PUBLICATION_DOMAINS = {
    "realpython.com", "infoq.com", "stackoverflow.com", "stackexchange.com",
    "dev.to", "medium.com", "geeksforgeeks.org", "towardsdatascience.com", "dzone.com"
}

INDEPENDENT_DB_DOMAINS = {
    "wikipedia.org", "wikidata.org", "imdb.com", "rottentomatoes.com",
    "censusindia.gov.in", "archive.org", "britannica.com"
}

PACKAGE_REGISTRIES = {
    "pypi.org", "npmjs.com", "crates.io", "pkg.go.dev", "packagist.org", "nuget.org", "rubygems.org"
}


# -------------------------
# DATA MODELS
# -------------------------
class SourceAssessment(BaseModel):
    source_id: str
    url: str
    domain: str
    provider: str = "gemini"
    authority_level: str = AuthorityLevel.UNKNOWN.value
    source_type: str = SourceCategory.UNKNOWN.value
    published_year: Optional[int] = None
    freshness_status: str = FreshnessLevel.UNKNOWN.value
    relevance_score: float = 0.0
    directness: str = "NO_SUPPORT"
    reliability_status: str = ReliabilityStatus.UNVERIFIED.value
    duplicate_status: str = DuplicateStatus.UNIQUE.value
    independence_status: str = IndependenceStatus.INDEPENDENT.value
    trust_reason: str = ""
    composite_selection_score: float = 0.0


class SourceConflict(BaseModel):
    conflict_type: str  # VALUE_CONFLICT, CHRONOLOGICAL_CONFLICT, SUPERLATIVE_CONFLICT
    attribute_name: str
    competing_claims: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_status: str = "UNRESOLVED"  # RESOLVED_PRIMARY, RESOLVED_FRESHNESS, UNRESOLVED
    winning_source_id: Optional[str] = None
    resolution_reason: str = ""


class EvidenceSelectionResult(BaseModel):
    selected_evidence: List[SourceAssessment] = Field(default_factory=list)
    rejected_evidence: List[SourceAssessment] = Field(default_factory=list)
    overall_status: str = "SUFFICIENT"  # SUFFICIENT, MULTI_SOURCE_SUPPORTED, CONFLICTED, STALE_EVIDENCE, INSUFFICIENT_TRUSTWORTHY_EVIDENCE
    diversity_count: int = 0
    conflicts_detected: List[SourceConflict] = Field(default_factory=list)
    selection_summary: str = ""


# -------------------------
# SOURCE CLASSIFICATION ENGINE
# -------------------------
class SourceTrustClassifier:
    """Classifies source authority, category, and initial reliability status based on domain and context."""

    @classmethod
    def classify_source(cls, url: str, domain: str, target_entity: Optional[str] = None) -> Tuple[str, str, str, str]:
        """
        Returns (authority_level, source_type, reliability_status, trust_reason).
        """
        if not domain and url:
            domain = urllib.parse.urlparse(url).netloc
        domain_lower = (domain or "").lower()
        url_lower = (url or "").lower()
        entity_lower = (target_entity or "").lower().replace(" ", "")

        # 1. Official Government & State Portals
        if (
            any(dom in domain_lower for dom in [".gov.in", ".nic.in", ".gov", ".gov.uk", "asi.nic.in"])
            or domain_lower.endswith(".gov.in")
            or domain_lower.endswith(".nic.in")
            or domain_lower.endswith(".gov")
            or ".ap.gov.in" in domain_lower
            or ".ts.gov.in" in domain_lower
        ):
            return AuthorityLevel.PRIMARY.value, SourceCategory.GOVERNMENT.value, ReliabilityStatus.TRUSTED.value, "Official government/state administrative portal."

        # 2. Official Software Documentation & Release Pages
        if any(dom in domain_lower for dom in PACKAGE_REGISTRIES):
            return AuthorityLevel.PRIMARY.value, SourceCategory.OFFICIAL_RELEASE.value, ReliabilityStatus.TRUSTED.value, "Official public package index/registry."

        if "github.com" in domain_lower and ("/releases" in url_lower or "/tags" in url_lower):
            return AuthorityLevel.PRIMARY.value, SourceCategory.OFFICIAL_RELEASE.value, ReliabilityStatus.TRUSTED.value, "Official repository release page."

        if domain_lower.startswith("docs.") or ".readthedocs.io" in domain_lower:
            return AuthorityLevel.PRIMARY.value, SourceCategory.OFFICIAL_DOCS.value, ReliabilityStatus.TRUSTED.value, "Dedicated technical documentation domain."

        # 3. Direct Entity Official Domain Matching (e.g. fastapi.tiangolo.com, python.org, ollama.com, kanakadurgamma.org)
        if entity_lower and len(entity_lower) >= 3:
            if entity_lower in domain_lower or domain_lower.startswith(entity_lower) or f"{entity_lower}." in domain_lower:
                return AuthorityLevel.PRIMARY.value, SourceCategory.OFFICIAL_COMPANY.value, ReliabilityStatus.TRUSTED.value, f"Canonical official domain matching entity '{target_entity}'."

        # 4. Established News Organizations
        if any(news_dom in domain_lower for news_dom in ESTABLISHED_NEWS_DOMAINS):
            return AuthorityLevel.SECONDARY.value, SourceCategory.ESTABLISHED_NEWS.value, ReliabilityStatus.TRUSTED.value, "Established national/international news publication."

        # 5. Technical Publications
        if any(tech_dom in domain_lower for tech_dom in TECH_PUBLICATION_DOMAINS):
            return AuthorityLevel.SECONDARY.value, SourceCategory.TECH_PUBLICATION.value, ReliabilityStatus.PROVISIONAL.value, "Recognized secondary technical publication/community."

        # 6. Independent Databases
        if any(db_dom in domain_lower for db_dom in INDEPENDENT_DB_DOMAINS):
            return AuthorityLevel.SECONDARY.value, SourceCategory.INDEPENDENT_DB.value, ReliabilityStatus.TRUSTED.value, "Independent public reference registry/database."

        # 7. Local Business / Restaurant Domains (Claim-dependent)
        if any(kw in domain_lower or kw in url_lower for kw in ["restaurant", "hotel", "cafe", "bistro", "bakery", "kitchen", "sweets"]):
            return AuthorityLevel.SECONDARY.value, SourceCategory.LOCAL_BUSINESS.value, ReliabilityStatus.PROVISIONAL.value, "Local business portal (Authoritative for self-attributes, not city-wide rankings)."

        # 8. Unclassified Blogs & General Web (Fail-Closed to UNKNOWN)
        return AuthorityLevel.UNKNOWN.value, SourceCategory.UNKNOWN.value, ReliabilityStatus.UNKNOWN.value, "Unverified/unrecognized third-party web source."


# -------------------------
# FRESHNESS EVALUATOR
# -------------------------
class FreshnessEvaluator:
    """Evaluates publication date against query temporal requirement."""

    @classmethod
    def extract_published_year(cls, text: str, url: str) -> Optional[int]:
        """Extracts publication or release year from URL paths or snippet text."""
        # Check URL patterns first (e.g. /2026/08/, /2026/, /releases/tag/v0.115.0)
        url_year_match = re.search(r"/(201\d|202\d)/", url)
        if url_year_match:
            return int(url_year_match.group(1))

        # Check snippet dates (e.g. "Released in 2026", "August 2026", "2026-08-15")
        text_date_match = re.search(r"\b(?:released|published|updated|in|dated)?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)?\s*(201\d|202\d)\b", text, re.IGNORECASE)
        if text_date_match:
            return int(text_date_match.group(1))

        return None

    @classmethod
    def evaluate_freshness(cls, published_year: Optional[int], temporal_requirement: str) -> Tuple[str, str]:
        """
        Returns (freshness_status, reason).
        temporal_requirement: 'CURRENT', 'RECENT', 'STABLE'
        """
        if temporal_requirement in ["CURRENT", "VERY_HIGH"]:
            if published_year is None:
                return FreshnessLevel.UNKNOWN.value, "Publication date unknown for temporal query."
            if published_year >= CURRENT_OPERATING_YEAR:
                return FreshnessLevel.CURRENT.value, f"Published in current operating year ({published_year})."
            elif published_year == CURRENT_OPERATING_YEAR - 1:
                return FreshnessLevel.RECENT.value, f"Published in previous year ({published_year})."
            else:
                return FreshnessLevel.STALE.value, f"Published in {published_year} (Stale for current query in {CURRENT_OPERATING_YEAR})."

        # For historical or general knowledge queries (LOW / STABLE requirement)
        if published_year is not None:
            return FreshnessLevel.CURRENT.value, f"Authoritative record dated {published_year} remains valid for stable topic."
        return FreshnessLevel.CURRENT.value, "General knowledge query does not require current publication date."


# -------------------------
# MULTI-SOURCE COMPARISON & CONFLICT RESOLUTION
# -------------------------
class ConflictResolutionEngine:
    """Compares multiple sources, identifies agreement, and resolves conflicts."""

    @classmethod
    def analyze_source_agreements_and_conflicts(
        cls,
        assessments: List[SourceAssessment],
        evidence_items: List[Dict[str, Any]],
        temporal_requirement: str
    ) -> Tuple[List[SourceConflict], str]:
        """
        Detects conflicts in extracted values (e.g. versions, dates) and determines resolution.
        """
        conflicts: List[SourceConflict] = []
        if len(assessments) < 2:
            return conflicts, "SUFFICIENT"

        # 1. Version Attribute Conflicts (e.g. FastAPI 0.115.0 vs 0.110.0)
        version_claims: List[Dict[str, Any]] = []
        for idx, itm in enumerate(evidence_items):
            content = itm.get("content", itm.get("snippet", ""))
            v_match = re.search(r"\b(?:v(?:ersion)?\.?\s*)?(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?)\b", content, re.IGNORECASE)
            if v_match and len(assessments) > idx:
                version_claims.append({
                    "source_id": assessments[idx].source_id,
                    "version": v_match.group(1),
                    "assessment": assessments[idx],
                    "content": content
                })

        distinct_versions = {vc["version"] for vc in version_claims}
        if len(distinct_versions) > 1:
            # Check if resolution is possible via Primary authority or Freshness
            competing = [{"source_id": vc["source_id"], "version": vc["version"], "authority": vc["assessment"].authority_level, "freshness": vc["assessment"].freshness_status} for vc in version_claims]
            
            # Find primary source
            primary_claims = [vc for vc in version_claims if vc["assessment"].authority_level == AuthorityLevel.PRIMARY.value]
            current_primary = [vc for vc in primary_claims if vc["assessment"].freshness_status == FreshnessLevel.CURRENT.value]

            if current_primary:
                winner = current_primary[0]
                conflicts.append(SourceConflict(
                    conflict_type="VALUE_CONFLICT",
                    attribute_name="version",
                    competing_claims=competing,
                    resolution_status="RESOLVED_PRIMARY",
                    winning_source_id=winner["source_id"],
                    resolution_reason=f"Resolved in favor of current primary source ({winner['assessment'].domain}) asserting version {winner['version']}."
                ))
            elif primary_claims:
                winner = primary_claims[0]
                conflicts.append(SourceConflict(
                    conflict_type="VALUE_CONFLICT",
                    attribute_name="version",
                    competing_claims=competing,
                    resolution_status="RESOLVED_PRIMARY",
                    winning_source_id=winner["source_id"],
                    resolution_reason=f"Resolved in favor of primary source ({winner['assessment'].domain}) asserting version {winner['version']}."
                ))
            else:
                conflicts.append(SourceConflict(
                    conflict_type="VALUE_CONFLICT",
                    attribute_name="version",
                    competing_claims=competing,
                    resolution_status="UNRESOLVED",
                    resolution_reason=f"Conflicting versions detected across sources ({', '.join(distinct_versions)}) without primary resolution."
                ))

        # 2. Chronological Year Conflicts (e.g. Founded in 1850 vs 1860)
        year_claims: List[Dict[str, Any]] = []
        for idx, itm in enumerate(evidence_items):
            content = itm.get("content", itm.get("snippet", ""))
            y_match = re.search(r"\b(?:founded|built|established|created|constructed)\s+(?:in|around|circa)?\s*(\d{4})\b", content, re.IGNORECASE)
            if y_match and len(assessments) > idx:
                year_claims.append({
                    "source_id": assessments[idx].source_id,
                    "year": y_match.group(1),
                    "assessment": assessments[idx]
                })

        distinct_years = {yc["year"] for yc in year_claims}
        if len(distinct_years) > 1:
            competing_years = [{"source_id": yc["source_id"], "year": yc["year"], "authority": yc["assessment"].authority_level} for yc in year_claims]
            conflicts.append(SourceConflict(
                conflict_type="CHRONOLOGICAL_CONFLICT",
                attribute_name="founding_year",
                competing_claims=competing_years,
                resolution_status="UNRESOLVED",
                resolution_reason=f"Sources disagree on the founding year ({', '.join(distinct_years)})."
            ))

        # Check for multi-source agreement: 2+ independent authoritative/secondary domains with high relevance
        unique_domains = {a.domain for a in assessments if a.authority_level in [AuthorityLevel.PRIMARY.value, AuthorityLevel.SECONDARY.value] and a.relevance_score >= 0.70}
        if len(unique_domains) >= 2 and not any(c.resolution_status == "UNRESOLVED" for c in conflicts):
            return conflicts, "MULTI_SOURCE_SUPPORTED"

        if any(c.resolution_status == "UNRESOLVED" for c in conflicts):
            return conflicts, "CONFLICTED"

        return conflicts, "SUFFICIENT"


# -------------------------
# EVIDENCE SELECTION ENGINE
# -------------------------
class EvidenceSelector:
    """Selects and ranks trustworthy evidence items using explainable composite scoring."""

    @classmethod
    def select_best_evidence(
        cls,
        raw_items: List[Dict[str, Any]],
        query: str,
        temporal_requirement: str = "CURRENT",
        target_entity: Optional[str] = None
    ) -> EvidenceSelectionResult:
        if not raw_items:
            return EvidenceSelectionResult(
                selected_evidence=[],
                rejected_evidence=[],
                overall_status="INSUFFICIENT_TRUSTWORTHY_EVIDENCE",
                selection_summary="No raw evidence items provided."
            )

        # 1. URL Deduplication & Domain Lineage
        unique_items, diversity_metrics = DeduplicationEngine.deduplicate(raw_items)
        seen_domains: Set[str] = set()

        assessments: List[SourceAssessment] = []

        for idx, item in enumerate(unique_items):
            url = item.get("canonical_url", item.get("url", ""))
            domain = item.get("domain") or urllib.parse.urlparse(url).netloc
            snippet = item.get("snippet", item.get("content", ""))

            # Classify Authority & Source Type
            auth, stype, rel_status, trust_reason = SourceTrustClassifier.classify_source(
                url=url,
                domain=domain,
                target_entity=target_entity
            )

            # Classify Freshness
            pub_year = FreshnessEvaluator.extract_published_year(snippet, url)
            freshness, fresh_reason = FreshnessEvaluator.evaluate_freshness(pub_year, temporal_requirement)

            # Directness & Relevance
            relevance = float(item.get("relevance_score", 0.85))
            directness = item.get("directness", "DIRECT" if relevance >= 0.70 else "INDIRECT")

            # Independence Status
            if domain in seen_domains:
                ind_status = IndependenceStatus.SAME_NETWORK.value
                dup_status = DuplicateStatus.SAME_DOMAIN_COPY.value
            else:
                ind_status = IndependenceStatus.INDEPENDENT.value
                dup_status = DuplicateStatus.UNIQUE.value
                seen_domains.add(domain)

            # Calculate Explainable Composite Score:
            # 0.35 * Relevance + 0.25 * Authority + 0.20 * Freshness + 0.10 * Directness + 0.10 * Independence
            auth_weight = 1.0 if auth == AuthorityLevel.PRIMARY.value else (0.75 if auth == AuthorityLevel.SECONDARY.value else 0.30)
            fresh_weight = 1.0 if freshness == FreshnessLevel.CURRENT.value else (0.70 if freshness == FreshnessLevel.RECENT.value else 0.20)
            direct_weight = 1.0 if directness == "DIRECT" else 0.50
            ind_weight = 1.0 if ind_status == IndependenceStatus.INDEPENDENT.value else 0.50

            composite_score = round(
                0.35 * relevance +
                0.25 * auth_weight +
                0.20 * fresh_weight +
                0.10 * direct_weight +
                0.10 * ind_weight,
                3
            )

            assessment = SourceAssessment(
                source_id=f"src-{idx+1}",
                url=url,
                domain=domain,
                provider=item.get("provider", "gemini"),
                authority_level=auth,
                source_type=stype,
                published_year=pub_year,
                freshness_status=freshness,
                relevance_score=relevance,
                directness=directness,
                reliability_status=rel_status,
                duplicate_status=dup_status,
                independence_status=ind_status,
                trust_reason=f"{trust_reason} Freshness: {fresh_reason}",
                composite_selection_score=composite_score
            )
            assessments.append(assessment)

        # 2. Analyze Agreements and Conflicts
        conflicts, agreement_status = ConflictResolutionEngine.analyze_source_agreements_and_conflicts(
            assessments=assessments,
            evidence_items=unique_items,
            temporal_requirement=temporal_requirement
        )

        # 3. Sort assessments by composite score descending
        assessments.sort(key=lambda a: a.composite_selection_score, reverse=True)

        # Filter trustworthy vs rejected
        selected = [a for a in assessments if a.relevance_score >= 0.40 and a.composite_selection_score >= 0.45]
        rejected = [a for a in assessments if a not in selected]

        # 4. Check for Freshness Failure or Insufficient Trustworthy Evidence
        if temporal_requirement in ["CURRENT", "VERY_HIGH"]:
            if selected and all(a.freshness_status == FreshnessLevel.STALE.value for a in selected):
                overall_status = "STALE_EVIDENCE"
            elif not selected or all(a.authority_level == AuthorityLevel.UNKNOWN.value and a.relevance_score < 0.50 for a in selected):
                overall_status = "INSUFFICIENT_TRUSTWORTHY_EVIDENCE"
            else:
                overall_status = agreement_status
        else:
            if not selected:
                overall_status = "INSUFFICIENT_TRUSTWORTHY_EVIDENCE"
            else:
                overall_status = agreement_status

        summary = f"Selected {len(selected)} sources from {len(unique_items)} unique items across {len(seen_domains)} domains. Status: {overall_status}."

        return EvidenceSelectionResult(
            selected_evidence=selected,
            rejected_evidence=rejected,
            overall_status=overall_status,
            diversity_count=len(seen_domains),
            conflicts_detected=conflicts,
            selection_summary=summary
        )
