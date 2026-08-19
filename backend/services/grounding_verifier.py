"""
Saki Claim-Level Grounding & Answer Verification Engine (Sprint 7)
Decomposes draft responses into discrete factual claims, matches claims against
retrieved evidence items, detects evidence contradictions, classifies direct vs indirect
support, and repairs/removes unsupported or hallucinated assertions before final delivery.
"""

import re
import time
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


# -------------------------
# ENUMS & CONSTANTS
# -------------------------
class SupportState(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class Directness(str, Enum):
    DIRECT_SUPPORT = "DIRECT_SUPPORT"
    INDIRECT_SUPPORT = "INDIRECT_SUPPORT"
    INSUFFICIENT = "INSUFFICIENT"
    NO_SUPPORT = "NO_SUPPORT"


class ClaimImportance(str, Enum):
    CRITICAL = "CRITICAL"  # versions, years, dates, prices, locations, person identities, historical facts
    NORMAL = "NORMAL"      # standard descriptive claims
    LOW = "LOW"            # conversational banter, commentary


class AnswerSourceMode(str, Enum):
    STATIC_KNOWLEDGE = "STATIC_KNOWLEDGE"
    WEB_GROUNDED = "WEB_GROUNDED"
    MEMORY_GROUNDED = "MEMORY_GROUNDED"
    MIXED = "MIXED"


# Conversational phrases and greetings that do not constitute factual claims
CONVERSATIONAL_FILLERS = [
    r"^hey(?: there)?\b",
    r"^hello\b",
    r"^hi\b",
    r"^good (?:morning|afternoon|evening)\b",
    r"\bwhat do you think\b",
    r"\blet me know\b",
    r"\bfeel free to\b",
    r"\bhow does that sound\b",
    r"\bhope this helps\b",
    r"\bcheers\b",
    r"\bthanks for asking\b",
    r"\bcan i help with\b",
    r"\bif you're curious\b",
    r"\bwhat were we looking at\b",
    r"\bi (?:don't|do not) have (?:verified|active|access|records)\b",
    r"\bi'm sorry, but i (?:don't|do not) have\b",
    r"\bcould you share official details\b",
    r"\bif you have any specific questions\b",
    r"\bwhy not hit up a local\b",
    r"\bhow about exploring\b",
    r"\bmaybe you could ask\b"
]

VERSION_REGEX = re.compile(r"\b(?:v(?:ersion)?\.?\s*)?(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?)\b", re.IGNORECASE)
YEAR_REGEX = re.compile(r"\b(1\d{3}|20\d{2})\b")
PRICE_REGEX = re.compile(r"[\$₹€£]\s*\d+(?:,\d+)*(?:\.\d+)?|\b\d+\s*(?:dollars|rupees|inr|usd|euros)\b", re.IGNORECASE)


# -------------------------
# DATA MODELS
# -------------------------
class GroundingClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"clm-{time.time_ns() % 1000000}")
    text: str
    sentence_index: int = 0
    importance: str = ClaimImportance.NORMAL.value
    evidence_ids: List[str] = Field(default_factory=list)
    support_status: str = SupportState.UNKNOWN.value
    directness: str = Directness.NO_SUPPORT.value
    confidence: float = 0.0
    contradiction_status: str = "NO_CONFLICT"
    supporting_evidence_snippets: List[str] = Field(default_factory=list)
    source_citations: List[Dict[str, str]] = Field(default_factory=list)
    reason: str = ""


class AnswerGroundingAssessment(BaseModel):
    grounding_status: str = "FULLY_SUPPORTED"  # FULLY_SUPPORTED, MOSTLY_SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE
    answer_source_mode: str = AnswerSourceMode.WEB_GROUNDED.value
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    critical_claims_supported: bool = True
    claims: List[GroundingClaim] = Field(default_factory=list)
    repaired_answer: str = ""
    verification_latency_ms: float = 0.0


# -------------------------
# CLAIM EXTRACTION ENGINE
# -------------------------
def extract_claims_from_text(text: str) -> List[GroundingClaim]:
    """
    Decomposes draft response into discrete factual propositions.
    Ignores pure greetings, pleasantries, questions, and conversational wrappers.
    """
    if not text or len(text.strip()) == 0:
        return []

    # Clean speaker tags and meta-framing
    cleaned_input = re.sub(r"^(?:assistant|saki|ai|\[assistant\]|\[saki\])\s*[-:：]?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned_input = re.sub(r"\bbased on (?:the )?(?:grounded )?(?:web )?evidence[^\n,.]*[,.]?", "", cleaned_input, flags=re.IGNORECASE)

    # Clean markdown headers, bullet symbols, and bold markers for parsing
    lines = cleaned_input.split("\n")
    sentences: List[Tuple[str, int]] = []
    sent_idx = 0

    for line in lines:
        line_clean = re.sub(r"^#{1,6}\s+", "", line).strip()
        line_clean = re.sub(r"^[-*•]\s+", "", line_clean).strip()
        line_clean = re.sub(r"^\d+\.\s+", "", line_clean).strip()
        if not line_clean or len(line_clean) < 4:
            continue

        # Split line by sentence boundaries (.!?) while avoiding abbreviations like v0.115.0 or e.g.
        raw_sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“])", line_clean)
        for s in raw_sents:
            s_str = s.strip()
            if s_str and len(s_str) > 5:
                sentences.append((s_str, sent_idx))
                sent_idx += 1

    extracted_claims: List[GroundingClaim] = []

    for s_text, s_idx in sentences:
        # Check if sentence is purely a conversational pleasantry
        s_lower = s_text.lower()
        if any(re.search(filler, s_lower) for filler in CONVERSATIONAL_FILLERS) and len(s_text.split()) <= 8:
            continue
        if s_text.endswith("?") and not any(kw in s_lower for kw in ["version", "price", "released", "built", "founded"]):
            continue

        # Check for compound clauses containing multiple propositions (e.g. "... and was built in 1500")
        sub_clauses = _split_compound_clauses(s_text)
        for clause in sub_clauses:
            clause_clean = clause.strip().rstrip(".,;!?")
            if len(clause_clean) < 6:
                continue

            importance = _determine_claim_importance(clause_clean)
            claim = GroundingClaim(
                claim_id=f"clm-{len(extracted_claims)+1}",
                text=clause_clean,
                sentence_index=s_idx,
                importance=importance
            )
            extracted_claims.append(claim)

    return extracted_claims


def _split_compound_clauses(sentence: str) -> List[str]:
    """
    Splits compound sentences with coordinating conjunctions ('and was built in', ', but was founded in')
    to isolate distinct factual assertions while preserving the main subject.
    """
    conjunction_pattern = re.compile(
        r"(?<=\w)\s+(?:and(?:\s+was|\s+is|\s+has|\s+dates)?|but(?:\s+was|\s+is|\s+has)?|while(?:\s+it\s+was)?)\s+(?=(?:built|founded|created|located|released|situated|dating|famous|known|developed|designed)\b)",
        re.IGNORECASE
    )
    parts = conjunction_pattern.split(sentence)
    if len(parts) <= 1:
        return [sentence]

    clauses = []
    base_subject = ""
    # Try to extract subject from first part
    subj_match = re.match(r"^([A-Z][a-zA-Z0-9_\s]{2,25}?(?:\s+(?:is|was|are|were|has|have)))\b", parts[0])
    if subj_match:
        base_subject = subj_match.group(1).split()[0]

    for i, p in enumerate(parts):
        p_clean = p.strip()
        if i > 0 and base_subject and not any(p_clean.lower().startswith(kw) for kw in ["it", "they", base_subject.lower()]):
            clauses.append(f"{base_subject} is {p_clean}")
        else:
            clauses.append(p_clean)

    return clauses


def _determine_claim_importance(text: str) -> str:
    """Classifies claim importance based on presence of sensitive/factual anchors."""
    text_lower = text.lower()
    if VERSION_REGEX.search(text):
        return ClaimImportance.CRITICAL.value
    if YEAR_REGEX.search(text):
        return ClaimImportance.CRITICAL.value
    if PRICE_REGEX.search(text):
        return ClaimImportance.CRITICAL.value
    if any(kw in text_lower for kw in [
        "founded", "built", "created", "released", "capital of", "invented by",
        "century", "dynasty", "king", "ruler", "temple", "river", "governor"
    ]):
        return ClaimImportance.CRITICAL.value
    if any(kw in text_lower for kw in ["best", "top rated", "ranked", "official", "famous for", "known for"]):
        return ClaimImportance.NORMAL.value
    return ClaimImportance.NORMAL.value


# -------------------------
# CLAIM MATCHING & VERIFICATION ENGINE
# -------------------------
class GroundingVerifierEngine:
    """
    Grounding and Answer Verification Subsystem.
    Matches extracted claims against retrieved evidence, checks for direct support,
    identifies multi-source contradictions, and repairs draft answers.
    """

    @classmethod
    def evaluate_answer_grounding(
        cls,
        draft_text: str,
        evidence_items: Optional[List[Any]] = None,
        evidence_package: Optional[Any] = None,
        action_decision: Optional[Any] = None,
        user_query: Optional[str] = None
    ) -> AnswerGroundingAssessment:
        t0 = time.time()
        claims = extract_claims_from_text(draft_text)

        # Determine Answer Source Mode
        requires_web = bool(action_decision and getattr(action_decision, "requires_world_access", False))
        has_evidence = bool(evidence_items or (evidence_package and getattr(evidence_package, "evidence_items", None)))

        if not requires_web and not has_evidence:
            source_mode = AnswerSourceMode.STATIC_KNOWLEDGE.value
        elif not requires_web and has_evidence:
            source_mode = AnswerSourceMode.MIXED.value
        else:
            source_mode = AnswerSourceMode.WEB_GROUNDED.value

        # Collect all evidence text and sources
        normalized_evidence: List[Dict[str, Any]] = []
        if evidence_package and getattr(evidence_package, "evidence_items", None):
            for itm in evidence_package.evidence_items:
                normalized_evidence.append({
                    "id": getattr(itm, "source_type", "src"),
                    "title": getattr(itm, "title", ""),
                    "content": getattr(itm, "content", ""),
                    "url": getattr(itm, "url", ""),
                    "domain": getattr(itm, "domain", "")
                })
        elif evidence_items:
            for itm in evidence_items:
                normalized_evidence.append({
                    "id": getattr(itm, "source_type", "src") if hasattr(itm, "source_type") else "src",
                    "title": getattr(itm, "title", "") if hasattr(itm, "title") else str(itm.get("title", "")),
                    "content": getattr(itm, "content", "") if hasattr(itm, "content") else str(itm.get("content", itm.get("snippet", ""))),
                    "url": getattr(itm, "url", "") if hasattr(itm, "url") else str(itm.get("url", "")),
                    "domain": getattr(itm, "domain", "") if hasattr(itm, "domain") else str(itm.get("domain", ""))
                })

        # Check for multi-source evidence contradictions first
        contradictions = cls.detect_evidence_contradictions(normalized_evidence)

        supported_count = 0
        unsupported_count = 0
        contradicted_count = 0
        critical_all_supported = True

        for claim in claims:
            # 1. Check if claim intersects with a known contradiction
            is_conflicted, conflict_reason = cls._check_claim_contradiction(claim.text, contradictions)
            if is_conflicted:
                claim.support_status = SupportState.CONTRADICTED.value
                claim.contradiction_status = "CONFLICTED"
                claim.directness = Directness.INSUFFICIENT.value
                claim.reason = conflict_reason
                contradicted_count += 1
                if claim.importance == ClaimImportance.CRITICAL.value:
                    critical_all_supported = False
                continue

            # 2. If STATIC_KNOWLEDGE mode (e.g. "What is FastAPI?"), general knowledge claims pass as SUPPORTED
            if source_mode == AnswerSourceMode.STATIC_KNOWLEDGE.value:
                claim.support_status = SupportState.SUPPORTED.value
                claim.directness = Directness.DIRECT_SUPPORT.value
                claim.confidence = 0.95
                claim.reason = "Supported by static model knowledge foundation."
                supported_count += 1
                continue

            # 3. If WEB_GROUNDED mode but no evidence was retrieved (e.g. rate limit, search failure)
            if source_mode == AnswerSourceMode.WEB_GROUNDED.value and not normalized_evidence:
                claim.support_status = SupportState.UNSUPPORTED.value
                claim.directness = Directness.NO_SUPPORT.value
                claim.confidence = 0.0
                claim.reason = "Web evidence was required but no verified sources were retrieved."
                unsupported_count += 1
                if claim.importance == ClaimImportance.CRITICAL.value:
                    critical_all_supported = False
                continue

            # 4. Match claim against retrieved evidence items
            match_res = cls.verify_claim_against_evidence(claim, normalized_evidence)
            claim.support_status = match_res["support_status"]
            claim.directness = match_res["directness"]
            claim.confidence = match_res["confidence"]
            claim.evidence_ids = match_res["evidence_ids"]
            claim.supporting_evidence_snippets = match_res["snippets"]
            claim.source_citations = match_res["citations"]
            claim.reason = match_res["reason"]

            if claim.support_status in [SupportState.SUPPORTED.value, SupportState.PARTIALLY_SUPPORTED.value]:
                supported_count += 1
            else:
                unsupported_count += 1
                if claim.importance == ClaimImportance.CRITICAL.value:
                    critical_all_supported = False

        # Compute overall Grounding Status
        if not claims:
            grounding_status = "FULLY_SUPPORTED"
        elif contradicted_count > 0:
            grounding_status = "CONTRADICTED"
        elif unsupported_count == 0:
            grounding_status = "FULLY_SUPPORTED"
        elif supported_count > 0 and unsupported_count <= len(claims) // 2 and critical_all_supported:
            grounding_status = "MOSTLY_SUPPORTED"
        elif supported_count > 0:
            grounding_status = "PARTIALLY_SUPPORTED"
        elif not normalized_evidence:
            grounding_status = "INSUFFICIENT_EVIDENCE"
        else:
            grounding_status = "UNSUPPORTED"

        # Step 5: Answer Repair
        repaired_answer = cls.repair_answer_grounding(
            draft_text=draft_text,
            claims=claims,
            contradictions=contradictions,
            source_mode=source_mode
        )

        elapsed_ms = (time.time() - t0) * 1000

        return AnswerGroundingAssessment(
            grounding_status=grounding_status,
            answer_source_mode=source_mode,
            total_claims=len(claims),
            supported_claims=supported_count,
            unsupported_claims=unsupported_count,
            contradicted_claims=contradicted_count,
            critical_claims_supported=critical_all_supported,
            claims=claims,
            repaired_answer=repaired_answer,
            verification_latency_ms=round(elapsed_ms, 2)
        )

    @classmethod
    def verify_claim_against_evidence(
        cls,
        claim: Any,
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates whether evidence items provide direct or indirect support for a specific claim.
        Accepts GroundingClaim or string.
        """
        if isinstance(claim, str):
            claim_text = claim
        else:
            claim_text = getattr(claim, "text", str(claim))

        claim_lower = claim_text.lower()
        matching_evidence_ids = []
        matching_snippets = []
        citations = []

        # Extract sensitive factual tokens
        version_match = VERSION_REGEX.search(claim_text)
        year_match = YEAR_REGEX.search(claim_text)

        # Token overlap setup
        claim_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", claim_lower))
        stop_words = {
            "the", "and", "for", "with", "this", "that", "from", "was", "are", "were",
            "been", "have", "has", "famous", "special", "known", "located", "situated",
            "traditional", "authentic", "also", "some", "such", "about", "into"
        }
        claim_keywords = claim_words - stop_words

        best_score = 0.0
        best_directness = Directness.NO_SUPPORT.value
        best_reason = "No matching evidence found in retrieved sources."

        for idx, ev in enumerate(evidence_list):
            ev_content = (ev.get("content", "") + " " + ev.get("title", "")).lower()
            ev_raw_content = ev.get("content", "")

            # 1. Version Check: If claim specifies a version, evidence MUST contain that version string
            if version_match:
                req_version = version_match.group(1).lower()
                if req_version not in ev_content:
                    # General doc without version -> INSUFFICIENT / NO_SUPPORT
                    continue
                else:
                    best_score = 0.98
                    best_directness = Directness.DIRECT_SUPPORT.value
                    best_reason = f"Exact version '{req_version}' verified in source."
                    matching_evidence_ids.append(f"ev-{idx+1}")
                    matching_snippets.append(ev_raw_content[:200])
                    citations.append({"url": ev.get("url", ""), "domain": ev.get("domain", ""), "title": ev.get("title", "")})
                    break

            # 2. Year/Date Check: If claim specifies a founding/building year, evidence MUST contain that year
            if year_match:
                req_year = year_match.group(1)
                if req_year not in ev_content:
                    continue
                else:
                    best_score = 0.95
                    best_directness = Directness.DIRECT_SUPPORT.value
                    best_reason = f"Historical year '{req_year}' verified in source."
                    matching_evidence_ids.append(f"ev-{idx+1}")
                    matching_snippets.append(ev_raw_content[:200])
                    citations.append({"url": ev.get("url", ""), "domain": ev.get("domain", ""), "title": ev.get("title", "")})
                    break

            # 3. Standard Keyword/Semantic Overlap
            if not claim_keywords:
                continue

            matched_kw = [kw for kw in claim_keywords if kw in ev_content]
            overlap_ratio = len(matched_kw) / len(claim_keywords)

            # Check for superlative mismatch (e.g. "one of the best" vs mere existence)
            has_superlative = any(sup in claim_lower for sup in ["best", "top", "famous", "renowned", "most popular", "number one", "greatest"])
            ev_has_superlative = any(sup in ev_content for sup in ["best", "top", "famous", "renowned", "special", "popular", "delicacy", "must-try"])

            # Claim-dependent trust check: Restaurant source claiming its own superlative ranking vs menu item
            ev_domain = (ev.get("domain") or "").lower()
            is_self_business_domain = any(kw in ev_domain for kw in ["restaurant", "hotel", "cafe", "bistro", "bakery", "kitchen", "sweets"])
            
            # Check if key named nouns match directly in evidence
            distinct_nouns = [kw for kw in claim_keywords if len(kw) >= 4 and kw in ev_content]

            if has_superlative and is_self_business_domain and not any(ind_kw in ev_domain for ind_kw in ["tourism", "news", "guide", "eater", "tripadvisor"]):
                # Self-asserted superlative ranking from business website is insufficient
                score = 0.40
                directness = Directness.INSUFFICIENT.value
                reason = "Self-asserted superlative ranking by business domain lacks independent third-party confirmation."
                if score > best_score:
                    best_score = score
                    best_directness = directness
                    best_reason = reason
            elif len(distinct_nouns) >= 3 or (len(distinct_nouns) >= 2 and overlap_ratio >= 0.25):
                score = 0.90
                directness = Directness.DIRECT_SUPPORT.value
                reason = f"Key named entities ({', '.join(distinct_nouns[:4])}) verified in source."
                if score > best_score:
                    best_score = score
                    best_directness = directness
                    best_reason = reason
                    matching_evidence_ids.append(f"ev-{idx+1}")
                    matching_snippets.append(ev_raw_content[:200])
                    citations.append({"url": ev.get("url", ""), "domain": ev.get("domain", ""), "title": ev.get("title", "")})
            elif overlap_ratio >= 0.75:
                if has_superlative and not ev_has_superlative:
                    score = 0.55
                    directness = Directness.INSUFFICIENT.value
                    reason = "Evidence confirms entity details but lacks superlative ranking assertion."
                else:
                    score = 0.90
                    directness = Directness.DIRECT_SUPPORT.value
                    reason = f"Strong lexical and semantic support ({int(overlap_ratio*100)}% match)."

                if score > best_score:
                    best_score = score
                    best_directness = directness
                    best_reason = reason
                    matching_evidence_ids.append(f"ev-{idx+1}")
                    matching_snippets.append(ev_raw_content[:200])
                    citations.append({"url": ev.get("url", ""), "domain": ev.get("domain", ""), "title": ev.get("title", "")})
            elif overlap_ratio >= 0.60:
                score = 0.50
                directness = Directness.INDIRECT_SUPPORT.value
                reason = "Partial/indirect context overlap."
                if score > best_score:
                    best_score = score
                    best_directness = directness
                    best_reason = reason

        # Determine SupportState from best_directness and best_score
        unique_citation_domains = {c.get("domain", "") for c in citations if c.get("domain")}
        contradiction_status = "MULTI_SOURCE_SUPPORTED" if len(unique_citation_domains) >= 2 else "NO_CONFLICT"

        if best_directness == Directness.DIRECT_SUPPORT.value and best_score >= 0.75:
            support_status = SupportState.SUPPORTED.value
        elif best_directness in [Directness.INDIRECT_SUPPORT.value, Directness.INSUFFICIENT.value] and best_score >= 0.40:
            support_status = SupportState.PARTIALLY_SUPPORTED.value
        else:
            support_status = SupportState.UNSUPPORTED.value
            best_directness = Directness.NO_SUPPORT.value

        return {
            "support_status": support_status,
            "directness": best_directness,
            "confidence": round(best_score, 2),
            "evidence_ids": matching_evidence_ids,
            "snippets": matching_snippets,
            "citations": citations,
            "contradiction_status": contradiction_status,
            "reason": best_reason
        }

    @classmethod
    def detect_evidence_contradictions(cls, evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifies factual contradictions across multiple sources (e.g. founded in 1850 vs founded in 1860).
        """
        contradictions = []
        if len(evidence_list) < 2:
            return contradictions

        year_mentions = []
        for idx, ev in enumerate(evidence_list):
            content = ev.get("content", "")
            # Look for founding/building year patterns like "founded in 1850", "built in 1860"
            founding_match = re.search(r"\b(?:founded|built|established|created|constructed)\s+(?:in|around|circa)?\s*(\d{4})\b", content, re.IGNORECASE)
            if founding_match:
                year = founding_match.group(1)
                year_mentions.append({
                    "source_idx": idx,
                    "year": year,
                    "title": ev.get("title", f"Source {idx+1}")
                })

        # Compare years
        if len(year_mentions) >= 2:
            distinct_years = {m["year"] for m in year_mentions}
            if len(distinct_years) > 1:
                contradictions.append({
                    "type": "CHRONOLOGICAL_CONTRADICTION",
                    "values": list(distinct_years),
                    "details": f"Sources disagree on the founding year ({', '.join(distinct_years)})."
                })

        return contradictions

    @classmethod
    def _check_claim_contradiction(
        cls,
        claim_text: str,
        contradictions: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        for c in contradictions:
            if c["type"] == "CHRONOLOGICAL_CONTRADICTION":
                for val in c["values"]:
                    if val in claim_text:
                        return True, c["details"]
        return False, ""

    @classmethod
    def repair_answer_grounding(
        cls,
        draft_text: str,
        claims: List[GroundingClaim],
        contradictions: List[Dict[str, Any]],
        source_mode: str
    ) -> str:
        """
        Repairs draft answer by removing unsupported critical claims, resolving
        compound sentences to preserve supported clauses, and qualifying contradictions.
        """
        if not claims:
            return draft_text

        # In STATIC_KNOWLEDGE mode, do not strip general knowledge
        if source_mode == AnswerSourceMode.STATIC_KNOWLEDGE.value:
            return draft_text

        unsupported_critical_claims = [
            c for c in claims
            if c.support_status == SupportState.UNSUPPORTED.value and c.importance == ClaimImportance.CRITICAL.value
        ]
        contradicted_claims = [
            c for c in claims
            if c.support_status == SupportState.CONTRADICTED.value
        ]

        if not unsupported_critical_claims and not contradicted_claims:
            return draft_text

        # Split original draft into paragraph blocks
        paragraphs = draft_text.split("\n\n")
        repaired_paras = []
        seen_clauses = set()

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue

            # Split paragraph into sentences
            raw_sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“])", para_clean)
            repaired_sents = []

            for sent in raw_sents:
                sent_clean = sent.strip()
                if not sent_clean:
                    continue

                # Check if this sentence contains an unsupported critical claim
                sent_unsupported = [
                    c for c in unsupported_critical_claims
                    if c.text.lower() in sent_clean.lower() or any(w in sent_clean.lower() for w in c.text.lower().split() if len(w) > 4)
                ]
                sent_contradicted = [
                    c for c in contradicted_claims
                    if any(val in sent_clean for val in c.reason.split() if val.isdigit())
                ]

                # Case A: Contradicted claim in sentence
                if sent_contradicted:
                    conflict_c = sent_contradicted[0]
                    # Replace with qualified uncertainty rather than fabricating resolution
                    qualified_sent = f"Sources disagree on the exact date or details regarding this ({conflict_c.reason})."
                    if qualified_sent not in seen_clauses:
                        repaired_sents.append(qualified_sent)
                        seen_clauses.add(qualified_sent)
                    continue

                # Case B: Unsupported critical claim in sentence
                if sent_unsupported:
                    # Check if sentence is compound (e.g. "Temple X is in Vijayawada and was built in 1500.")
                    # Try to isolate supported portion
                    supported_clauses = [
                        c for c in claims
                        if c.support_status == SupportState.SUPPORTED.value and (c.text.lower() in sent_clean.lower() or any(w in sent_clean.lower() for w in c.text.lower().split() if len(w) > 4))
                    ]
                    if supported_clauses:
                        best_sup = supported_clauses[0].text.strip().rstrip(".")
                        if best_sup not in seen_clauses:
                            repaired_sents.append(f"{best_sup}.")
                            seen_clauses.add(best_sup)
                    else:
                        # Drop the sentence completely
                        continue
                else:
                    if sent_clean not in seen_clauses:
                        repaired_sents.append(sent_clean)
                        seen_clauses.add(sent_clean)

            if repaired_sents:
                repaired_paras.append(" ".join(repaired_sents))

        repaired_text = "\n\n".join(repaired_paras).strip()

        # If all content was stripped (e.g. query had only 1 sentence that was unsupported)
        if not repaired_text or len(repaired_text) < 15:
            repaired_text = "Hey there! 😊 I don't have verified records or active web search results to confirm those specific details right now."

        return repaired_text
