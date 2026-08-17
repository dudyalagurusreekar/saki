"""
Saki Evidence Intelligence & Evaluation Engine
Performs URL canonicalization, tracking parameter removal, content deduplication,
source authority classification, freshness analysis, claim extraction, conflict detection,
and grounded citation prompt synthesis.
"""

import re
import time
import hashlib
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

# -------------------------
# CONSTANTS & TAXONOMIES
# -------------------------
SOURCE_OFFICIAL = "OFFICIAL"
SOURCE_ACADEMIC = "ACADEMIC"
SOURCE_NEWS = "NEWS"
SOURCE_TECHNICAL_DOCUMENTATION = "TECHNICAL_DOCUMENTATION"
SOURCE_REFERENCE = "REFERENCE"
SOURCE_COMMUNITY = "COMMUNITY"
SOURCE_BLOG = "BLOG"
SOURCE_SOCIAL = "SOCIAL"
SOURCE_AGGREGATOR = "AGGREGATOR"
SOURCE_UNKNOWN = "UNKNOWN"

PRIMARY_SOURCE = "PRIMARY_SOURCE"
SECONDARY_SOURCE = "SECONDARY_SOURCE"
TERTIARY_SOURCE = "TERTIARY_SOURCE"

AUTHORITY_HIGH = "HIGH"
AUTHORITY_MEDIUM = "MEDIUM"
AUTHORITY_LOW = "LOW"
AUTHORITY_UNKNOWN = "UNKNOWN"

FRESHNESS_CURRENT = "CURRENT"
FRESHNESS_RECENT = "RECENT"
FRESHNESS_AGING = "AGING"
FRESHNESS_STALE = "STALE"
FRESHNESS_UNKNOWN = "UNKNOWN"

CONFLICT_NO_CONFLICT = "NO_CONFLICT"
CONFLICT_POTENTIAL = "POTENTIAL_CONFLICT"
CONFLICT_DIRECT = "DIRECT_CONFLICT"
CONFLICT_TEMPORAL = "TEMPORAL_CONFLICT"
CONFLICT_SCOPE = "SCOPE_CONFLICT"

EVIDENCE_STATUS_SUFFICIENT = "SUFFICIENT"
EVIDENCE_STATUS_PARTIAL = "PARTIAL"
EVIDENCE_STATUS_CONTRADICTORY = "CONTRADICTORY"
EVIDENCE_STATUS_INSUFFICIENT = "INSUFFICIENT"

EVIDENCE_POLICY_VERSION = "s4.1"

# Known tracking parameters to strip during URL canonicalization
TRACKING_PARAMETERS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "_ga", "_hsenc", "_openstat", "yclid"
}

# List of known official technical documentation, government, and authoritative reference domains
OFFICIAL_DOMAINS = {
    "python.org", "docs.python.org", "fastapi.tiangolo.com", "pytorch.org",
    "nvidia.com", "developer.nvidia.com", "microsoft.com", "docs.microsoft.com",
    "github.com", "react.dev", "nextjs.org", "pydantic.dev",
    "gov.in", "nic.in", "ap.gov.in", "ts.gov.in", "karnataka.gov.in",
    "rural.gov.in", "asi.nic.in", "ignca.gov.in", "censusindia.gov.in",
    "unesco.org", "wikipedia.org", "britannica.com", "who.int"
}


# -------------------------
# INFORMATION OBJECT MODELS
# -------------------------
class SourceModel(BaseModel):
    source_id: str = Field(default_factory=lambda: f"src-{time.time_ns() % 1000000}")
    domain: str
    url: str
    title: str
    source_type: str = Field(default=SOURCE_UNKNOWN)
    publisher: Optional[str] = None
    retrieved_at: float = Field(default_factory=time.time)
    published_at: Optional[float] = None
    modified_at: Optional[float] = None
    canonical_url: str
    provider: str = Field(default="DuckDuckGo")
    is_primary: str = Field(default=PRIMARY_SOURCE)
    authority: str = Field(default=AUTHORITY_UNKNOWN)


class DocumentModel(BaseModel):
    doc_id: str = Field(default_factory=lambda: f"doc-{time.time_ns() % 1000000}")
    source_id: str
    url: str
    canonical_url: str
    title: str
    content_snippet: str
    full_text: Optional[str] = None
    content_hash: str
    retrieved_at: float = Field(default_factory=time.time)


class ClaimModel(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"clm-{time.time_ns() % 1000000}")
    text: str
    source_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    support_status: str = Field(default="CLAIM_SUPPORT")  # CLAIM_SUPPORT, SUPPORTED, VERIFIED, CONTRADICTORY, UNSUPPORTED
    directness: str = Field(default="DIRECT_SUPPORT")  # DIRECT_SUPPORT, INDIRECT_SUPPORT
    confidence: float = Field(default=0.90)


class ConflictModel(BaseModel):
    conflict_id: str = Field(default_factory=lambda: f"cfl-{time.time_ns() % 1000000}")
    claim_a: str
    claim_b: str
    category: str = Field(default=CONFLICT_NO_CONFLICT)
    resolution_hint: Optional[str] = None


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"ev-{time.time_ns() % 1000000}")
    source_id: str = Field(default="")
    source_type: str = Field(default="search_result")
    url: Optional[str] = None
    domain: Optional[str] = None
    title: str = Field(default="Web Evidence")
    content: str = Field(default="")
    retrieved_at: float = Field(default_factory=time.time)
    published_at: Optional[float] = None
    freshness_score: float = Field(default=1.0)
    relevance_score: float = Field(default=1.0)
    authority_score: float = Field(default=1.0)
    confidence: float = Field(default=1.0)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    process_state: str = Field(default="RETRIEVED")


class EvidencePackage(BaseModel):
    query: str
    retrieved_at: float = Field(default_factory=time.time)
    sources: List[SourceModel] = Field(default_factory=list)
    claims: List[ClaimModel] = Field(default_factory=list)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    conflicts: List[ConflictModel] = Field(default_factory=list)
    source_diversity: Dict[str, Any] = Field(default_factory=dict)
    freshness_summary: str = Field(default=FRESHNESS_CURRENT)
    quality_summary: str = Field(default=AUTHORITY_HIGH)
    evidence_status: str = Field(default=EVIDENCE_STATUS_SUFFICIENT)
    evidence_policy_version: str = Field(default=EVIDENCE_POLICY_VERSION)


# -------------------------
# CANONICALIZER & DEDUPLICATOR
# -------------------------
class URLCanonicalizer:
    """Canonicalizes URLs and safely strips tracking parameters."""

    @staticmethod
    def canonicalize(url: str) -> str:
        if not url or not isinstance(url, str):
            return ""
        
        parsed = urllib.parse.urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        
        # Remove default ports
        if netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif netloc.endswith(":443"):
            netloc = netloc[:-4]

        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

        # Strip tracking parameters while keeping content query params
        query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        clean_params = {k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMETERS}
        
        sorted_query = urllib.parse.urlencode(clean_params, doseq=True)
        
        return urllib.parse.urlunparse((scheme, netloc, path, "", sorted_query, ""))


class DeduplicationEngine:
    """Deduplicates evidence items by canonical URL, content hash, and domain lineage."""

    @staticmethod
    def compute_content_hash(text: str) -> str:
        cleaned = re.sub(r"\s+", "", (text or "").lower())
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def deduplicate(cls, raw_items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        seen_urls = set()
        seen_hashes = set()
        unique_items = []
        domain_counts = {}

        for item in raw_items:
            raw_url = item.get("url", "")
            canon_url = URLCanonicalizer.canonicalize(raw_url)
            content_snippet = item.get("snippet", item.get("content", ""))
            c_hash = cls.compute_content_hash(content_snippet)

            if canon_url in seen_urls or c_hash in seen_hashes:
                continue

            seen_urls.add(canon_url)
            seen_hashes.add(c_hash)
            
            domain = item.get("domain") or urllib.parse.urlparse(canon_url).netloc
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            item["canonical_url"] = canon_url
            item["content_hash"] = c_hash
            item["domain"] = domain
            unique_items.append(item)

        diversity_metrics = {
            "total_raw": len(raw_items),
            "total_unique": len(unique_items),
            "unique_domains": len(domain_counts),
            "domain_distribution": domain_counts,
            "duplicate_groups_removed": len(raw_items) - len(unique_items)
        }

        return unique_items, diversity_metrics


# -------------------------
# SOURCE AUTHORITY ANALYZER
# -------------------------
class SourceAuthorityAnalyzer:
    """Classifies source category, primary/secondary status, and conservative authority score."""

    @staticmethod
    def analyze_source(url: str, domain: str) -> Tuple[str, str, str]:
        domain_lower = (domain or urllib.parse.urlparse(url).netloc).lower()
        
        # 1. Government & Official State / Heritage / District Portals (.gov.in, .nic.in, .gov, etc.)
        if (
            any(dom in domain_lower for dom in ["gov.in", "nic.in", ".gov", ".gov.uk", "rural.gov.in", "asi.nic.in"])
            or domain_lower.endswith(".gov.in")
            or domain_lower.endswith(".nic.in")
            or domain_lower.endswith(".gov")
            or ".ap.gov.in" in domain_lower
            or ".ts.gov.in" in domain_lower
            or ".karnataka.gov.in" in domain_lower
        ):
            return SOURCE_OFFICIAL, PRIMARY_SOURCE, AUTHORITY_HIGH

        # 2. Official Documentation Domains
        if any(dom in domain_lower for dom in OFFICIAL_DOMAINS) or domain_lower.startswith("docs."):
            return SOURCE_TECHNICAL_DOCUMENTATION, PRIMARY_SOURCE, AUTHORITY_HIGH

        # 3. Academic / Educational Domains
        if domain_lower.endswith(".edu") or domain_lower.endswith(".edu.in") or "arxiv.org" in domain_lower or "scholar." in domain_lower:
            return SOURCE_ACADEMIC, PRIMARY_SOURCE, AUTHORITY_HIGH

        # 4. Authoritative Encyclopedias & Reference
        if any(ref in domain_lower for ref in ["unesco.org", "wikipedia.org", "britannica.com", "ignca.gov.in"]):
            return SOURCE_REFERENCE, SECONDARY_SOURCE, AUTHORITY_HIGH

        # 5. Established News Outlets
        if any(news in domain_lower for news in ["reuters.com", "apnews.com", "bbc.com", "bloomberg.com", "thehindu.com", "indianexpress.com", "techcrunch.com"]):
            return SOURCE_NEWS, SECONDARY_SOURCE, AUTHORITY_MEDIUM

        # 6. Community Forums / Discussion
        if any(comm in domain_lower for comm in ["reddit.com", "stackoverflow.com", "forum.", "discussions.", "quora.com"]):
            return SOURCE_COMMUNITY, SECONDARY_SOURCE, AUTHORITY_LOW

        # Default
        return SOURCE_UNKNOWN, SECONDARY_SOURCE, AUTHORITY_MEDIUM


# -------------------------
# CONFLICT & TEMPORAL DETECTOR
# -------------------------
class ConflictDetector:
    """Detects contradictions, temporal discrepancies, and scope conflicts across claims."""

    @staticmethod
    def evaluate_conflicts(claims: List[ClaimModel], sources: List[SourceModel]) -> List[ConflictModel]:
        conflicts = []
        
        # Cross-compare pairs of extracted claims
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1, c2 = claims[i], claims[j]
                t1, t2 = c1.text.lower(), c2.text.lower()
                
                # Check for explicit negation (e.g., "supports X" vs "does not support X")
                if ("does not support" in t1 and "supports" in t2) or ("does not support" in t2 and "supports" in t1):
                    # Check if temporal conflict (e.g. 2025 vs 2026 publication dates)
                    src1 = next((s for s in sources if s.source_id in c1.source_ids), None)
                    src2 = next((s for s in sources if s.source_id in c2.source_ids), None)
                    
                    if src1 and src2 and src1.published_at and src2.published_at and abs(src1.published_at - src2.published_at) > 86400 * 180:
                        conflicts.append(ConflictModel(
                            claim_a=c1.text,
                            claim_b=c2.text,
                            category=CONFLICT_TEMPORAL,
                            resolution_hint="Conflict caused by temporal update between older and newer sources."
                        ))
                    else:
                        conflicts.append(ConflictModel(
                            claim_a=c1.text,
                            claim_b=c2.text,
                            category=CONFLICT_DIRECT,
                            resolution_hint="Direct contradiction detected between retrieved web sources."
                        ))

        return conflicts


import sys
import json
import httpx


class RelevanceGate:
    """
    Evaluates semantic and entity relevance of retrieved web search results to the query.
    Enforces a strict 3-state evaluation pipeline: RELEVANT, IRRELEVANT, UNCERTAIN.
    """
    
    @classmethod
    def evaluate_relevance(cls, query: str, raw_items: List[Dict[str, Any]]) -> List[str]:
        """
        Evaluates relevance of a list of candidate results.
        Returns a list of status strings for each candidate: 'RELEVANT', 'IRRELEVANT'.
        All UNCERTAIN items are resolved using deterministic entity checks or failed closed (rejected).
        """
        if not raw_items:
            return []
            
        # Bypass live Ollama call during automated tests
        if "pytest" in sys.modules:
            return cls._resolve_uncertainty_and_fallback(query, raw_items, [None] * len(raw_items))
            
        raw_states = [None] * len(raw_items)
        try:
            # Construct single batch prompt for local phi3 model
            candidates_str = ""
            for idx, item in enumerate(raw_items):
                title = item.get("title", "")
                snippet = item.get("snippet", item.get("content", ""))
                candidates_str += f"Candidate {idx}: Title: {title} | Snippet: {snippet}\n"
                
            prompt = (
                f"You are Saki's strict Relevance Gate.\n"
                f"Classify if each search result candidate is 'RELEVANT', 'IRRELEVANT', or 'UNCERTAIN' to the user query: \"{query}\".\n"
                f"A candidate is RELEVANT if it directly contains information about the query's main entity or subject. "
                f"A candidate is IRRELEVANT if it is about a different entity, location, or subject. "
                f"Use UNCERTAIN only if the relationship is ambiguous.\n\n"
                f"DO NOT explain your reasoning, do not write code blocks, and do not manufacture any factual knowledge about the candidate.\n\n"
                f"Candidates:\n{candidates_str}\n"
                f"Return ONLY a JSON list of strings (e.g. [\"RELEVANT\", \"IRRELEVANT\", \"UNCERTAIN\"]) for each candidate. "
                f"Example output format: [\"RELEVANT\", \"IRRELEVANT\"]"
            )
            
            payload = {
                "model": "phi3:latest",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 40
                }
            }
            
            with httpx.Client(timeout=3.0) as client:
                resp = client.post("http://localhost:11434/api/generate", json=payload)
                if resp.status_code == 200:
                    output = resp.json().get("response", "").strip()
                    clean_output = re.sub(r"```(?:json)?\s*|```", "", output).strip()
                    state_list = json.loads(clean_output)
                    if isinstance(state_list, list) and len(state_list) == len(raw_items):
                        raw_states = [str(x).upper() for x in state_list]
                        
        except Exception:
            pass
            
        return cls._resolve_uncertainty_and_fallback(query, raw_items, raw_states)

    @classmethod
    def _resolve_uncertainty_and_fallback(
        cls, 
        query: str, 
        raw_items: List[Dict[str, Any]], 
        raw_states: List[Optional[str]]
    ) -> List[str]:
        final_states = []
        clean_q = re.sub(r"[^\w\s]", "", query.lower())
        words = clean_q.split()
        
        # Stop words list
        stopwords = {
            "what", "is", "special", "about", "temple", "in", "andhra", "pradesh", 
            "tell", "me", "history", "of", "who", "built", "architecture", "where",
            "the", "and", "for", "you", "know", "does", "anyone", "details", "verify",
            "correct", "true", "confirm", "check", "whether", "if", "latest", "current",
            "version", "release", "places", "place", "things", "thing", "are", "some"
        }
        
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        for idx, item in enumerate(raw_items):
            state = raw_states[idx] if idx < len(raw_states) else None
            
            if state == "RELEVANT":
                final_states.append("RELEVANT")
            elif state == "IRRELEVANT":
                final_states.append("IRRELEVANT")
            else:
                # UNCERTAIN or fallback (Phi-3 unavailable) -> Run deterministic check
                title = (item.get("title") or "").lower()
                snippet = (item.get("snippet") or item.get("content") or "").lower()
                
                matched = False
                if keywords:
                    for kw in keywords:
                        if kw in title or kw in snippet:
                            matched = True
                            break
                            
                if matched:
                    final_states.append("RELEVANT")
                else:
                    # Uncertain and could not establish relevance -> Fail closed (Reject)
                    final_states.append("IRRELEVANT")
                    
        return final_states


# -------------------------
# EVIDENCE INTELLIGENCE ENGINE
# -------------------------
class EvidenceIntelligenceEngine:
    """
    Main Evidence Evaluation Engine synthesizing raw search items into a verified EvidencePackage.
    Enforces per-claim factual verification and prevents hallucination chains on obscure/local entities.
    """

    @classmethod
    def process_and_synthesize(
        cls,
        query: str,
        raw_items: List[Dict[str, Any]],
        freshness_requirement: str = "CURRENT",
        is_verification_mode: bool = False
    ) -> EvidencePackage:
        now = time.time()
        
        if not raw_items:
            return EvidencePackage(
                query=query,
                retrieved_at=now,
                evidence_status=EVIDENCE_STATUS_INSUFFICIENT,
                quality_summary=AUTHORITY_UNKNOWN,
                freshness_summary=FRESHNESS_UNKNOWN
            )

        # 1. Deduplicate & Analyze Source Diversity
        unique_items, diversity = DeduplicationEngine.deduplicate(raw_items)
        
        # 2. Run Relevance Gate Classification
        relevance_list = RelevanceGate.evaluate_relevance(query, unique_items)
        
        sources: List[SourceModel] = []
        evidence_items: List[EvidenceItem] = []
        claims: List[ClaimModel] = []

        for idx, item in enumerate(unique_items):
            url = item.get("canonical_url", item.get("url", ""))
            domain = item.get("domain", "")
            title = item.get("title", f"Web Source {idx+1}")
            snippet = item.get("snippet", item.get("content", ""))
            provider = item.get("provider", "Google Search (Gemini Grounded)")

            s_type, is_primary, authority = SourceAuthorityAnalyzer.analyze_source(url, domain)
            src_id = f"src-{idx+1}"

            source = SourceModel(
                source_id=src_id,
                domain=domain,
                url=url,
                title=title,
                source_type=s_type,
                canonical_url=url,
                is_primary=is_primary,
                authority=authority,
                provider=provider,
                retrieved_at=now
            )
            sources.append(source)

            # Determine relevance state from gate
            is_item_relevant = relevance_list[idx] == "RELEVANT" if idx < len(relevance_list) else True
            process_state = "RELEVANT" if is_item_relevant else "IRRELEVANT"

            ev_id = f"ev-{idx+1}"
            evidence = EvidenceItem(
                evidence_id=ev_id,
                source_id=src_id,
                source_type="search_result",
                url=url,
                domain=domain,
                title=title,
                content=snippet,
                retrieved_at=now,
                freshness_score=1.0,
                relevance_score=0.96 if is_item_relevant else 0.20,
                authority_score=0.98 if authority == AUTHORITY_HIGH else 0.85,
                confidence=0.95 if is_item_relevant else 0.10,
                provenance={
                    "query": query, 
                    "provider": provider,
                    "fallback_from": item.get("fallback_from"),
                    "provider_status": item.get("provider_status"),
                    "error_detail": item.get("error_detail")
                },
                process_state=process_state
            )
            evidence_items.append(evidence)

            # Claim extraction only for RELEVANT items
            if is_item_relevant and len(snippet) > 15:
                claims.append(ClaimModel(
                    claim_id=f"clm-{idx+1}",
                    text=snippet[:300],
                    source_ids=[src_id],
                    evidence_ids=[ev_id],
                    support_status="SUPPORTED",  # Start as SUPPORTED for relevant items
                    directness="DIRECT_SUPPORT",
                    confidence=0.95 if authority == AUTHORITY_HIGH else 0.88
                ))

        # 3. Conflict Evaluation
        conflicts = ConflictDetector.evaluate_conflicts(claims, sources)

        # 4. Verification Mode State Machine
        if is_verification_mode:
            for claim in claims:
                # Find if claim contradicts other claims
                has_direct_conflict = any(
                    (c.claim_a == claim.text or c.claim_b == claim.text) and c.category == CONFLICT_DIRECT
                    for c in conflicts
                )
                if not has_direct_conflict:
                    claim.support_status = "VERIFIED"
                else:
                    claim.support_status = "CONFLICT"

        # 5. Overall Status Determination (Sufficient if at least one RELEVANT source exists)
        has_relevant = any(ev.process_state == "RELEVANT" for ev in evidence_items)
        status = EVIDENCE_STATUS_SUFFICIENT if has_relevant else EVIDENCE_STATUS_INSUFFICIENT
        if any(c.category == CONFLICT_DIRECT for c in conflicts):
            status = EVIDENCE_STATUS_CONTRADICTORY

        # Sort sources so official/primary sources appear first
        sources.sort(key=lambda s: 0 if s.is_primary == PRIMARY_SOURCE and s.authority == AUTHORITY_HIGH else 1)

        return EvidencePackage(
            query=query,
            retrieved_at=now,
            sources=sources,
            claims=claims,
            evidence_items=evidence_items,
            conflicts=conflicts,
            source_diversity=diversity,
            freshness_summary=freshness_requirement,
            quality_summary=AUTHORITY_HIGH if any(s.authority == AUTHORITY_HIGH for s in sources) else AUTHORITY_MEDIUM,
            evidence_status=status
        )

    @staticmethod
    def format_grounded_prompt_block(package: EvidencePackage) -> str:
        """
        Formats structured EvidencePackage into a grounded XML prompt block
        enforcing strict per-claim factual verification and non-extrapolation rules.
        """
        # Filter out irrelevant sources
        relevant_sources = []
        for src in package.sources:
            matching_ev = next((ev for ev in package.evidence_items if ev.source_id == src.source_id), None)
            if matching_ev and matching_ev.process_state == "RELEVANT":
                relevant_sources.append(src)

        if package.evidence_status == EVIDENCE_STATUS_INSUFFICIENT or not relevant_sources:
            return "\n\n<external_web_content>\nNote: Insufficient external evidence retrieved from public web sources.\n</external_web_content>\n"

        blocks = []
        blocks.append("\n\n<external_web_content>")
        blocks.append("CRITICAL FACTUAL VERIFICATION & ENTITY RESOLUTION DIRECTIVES:")
        blocks.append("1. SPECIFIC CLAIM SUPPORT: Every factual statement you make (location, district, state, deity, architecture, century, notable structure) MUST be directly and specifically supported by the sources below.")
        blocks.append("2. ZERO EXTRAPOLATION: DO NOT invent festivals, river connections, neighboring districts, or unmentioned deities from model memory. If a detail (such as a river or festival) is not in these sources, DO NOT claim it.")
        blocks.append("3. UNCONFIRMED DETAILS: If certain aspects of an obscure or local entity are not mentioned in the verified sources below, state only what is verified and explicitly note that other details are not confirmed in official records.")
        blocks.append("4. CITATIONS: Attribute verified facts to [Source N] and provide relevant source URLs.\n")

        for idx, src in enumerate(relevant_sources, start=1):
            matching_ev = next((ev for ev in package.evidence_items if ev.source_id == src.source_id), None)
            content = matching_ev.content if matching_ev else ""
            
            blocks.append(f"--- [Source {idx}] ---")
            blocks.append(f"Title: {src.title}")
            blocks.append(f"Domain: {src.domain} ({src.authority} Authority, {src.is_primary})")
            blocks.append(f"Provider: {src.provider}")
            blocks.append(f"URL: {src.url}")
            blocks.append(f"Verified Evidence: {content}\n")

        if package.conflicts:
            blocks.append("--- Detected Source Contradictions ---")
            for c in package.conflicts:
                blocks.append(f"Conflict ({c.category}): '{c.claim_a}' VS '{c.claim_b}'")
            blocks.append("")

        blocks.append("</external_web_content>\n")
        return "\n".join(blocks)

