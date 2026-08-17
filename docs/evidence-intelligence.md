# Saki AI — Evidence Intelligence & Evaluation Engine Specification
**Sprint 4 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Evidence Evaluation & Grounding Engine  

---

## 1. EVIDENCE ARCHITECTURE

The Evidence Intelligence & Evaluation Engine evaluates, deduplicates, verifies, and maps citations for retrieved web data before context injection into local LLMs:

```
                  [ Raw Web Retrieval (Sprint 3) ]
                                │
                                ▼
           [ URLCanonicalizer & Tracking Parameter Scrubber ]
           (Strips utm_*, fbclid; normalizes scheme/hostname/path)
                                │
                                ▼
           [ Deduplication Engine (backend/services/evidence_engine.py) ]
           (Level 1 Canonical URL, Level 2 Document Hash, Level 3 Content Hash)
                                │
                                ▼
           [ Source Authority & Source Diversity Analyzer ]
           (Classifies OFFICIAL, TECHNICAL, ACADEMIC, NEWS vs COMMUNITY/BLOG; Primary vs Secondary)
                                │
                                ▼
           [ Topic-Aware Freshness & Relevance Engine ]
           (Compares timestamps vs LIVE, CURRENT, STABLE freshness requirements)
                                │
                                ▼
           [ Claim Extractor & Cross-Source Conflict Detector ]
           (Identifies DIRECT_CONFLICT, TEMPORAL_CONFLICT, SCOPE_CONFLICT)
                                │
                                ▼
                       [ EvidencePackage ]
                                │
                                ▼
           [ Grounded Prompt Synthesizer + XML Sandbox ]
           (Formats <external_web_content> with [Source 1..N] Citation Tags)
                                │
                                ▼
                     [ Local LLMs (Phi-3/Qwen-3) ]
```

---

## 2. INFORMATION OBJECT HIERARCHY

```
SEARCH RESULT (Provider level item)
    │
    ▼
SOURCE (Origin domain / publisher)
    │
    ▼
DOCUMENT (Specific canonical webpage / article)
    │
    ▼
CLAIM (Factual proposition extracted from content)
    │
    ▼
EVIDENCE (Supporting or contradicting text content)
    │
    ▼
EVIDENCE PACKAGE (Synthesized bundle passed to LLM)
    │
    ▼
GROUNDED ANSWER (Final response with [Source N] citations)
```

---

## 3. DATA MODELS

### SourceModel
- `source_id`: Unique identifier (`src-1`)
- `domain`: Origin domain (`docs.python.org`)
- `url`: Canonical URL
- `source_type`: `OFFICIAL`, `ACADEMIC`, `NEWS`, `TECHNICAL_DOCUMENTATION`, `REFERENCE`, `COMMUNITY`, `BLOG`, `UNKNOWN`
- `is_primary`: `PRIMARY_SOURCE`, `SECONDARY_SOURCE`, `TERTIARY_SOURCE`
- `authority`: `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`

### ClaimModel
- `claim_id`: Unique claim ID (`clm-1`)
- `text`: Fact text
- `source_ids`: List of supporting source IDs
- `support_status`: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTRADICTED`, `UNSUPPORTED`
- `directness`: `DIRECT_SUPPORT`, `INDIRECT_SUPPORT`

### ConflictModel
- `conflict_id`: Conflict ID (`cfl-1`)
- `claim_a`, `claim_b`: Contradicting claim statements
- `category`: `NO_CONFLICT`, `DIRECT_CONFLICT`, `TEMPORAL_CONFLICT`, `SCOPE_CONFLICT`

### EvidencePackage
- `query`: Outbound query string
- `sources`: List of canonical `SourceModel` items
- `claims`: List of `ClaimModel` items
- `conflicts`: List of `ConflictModel` items
- `source_diversity`: Diversity metrics (`unique_domains`, `duplicate_groups_removed`)
- `evidence_status`: `SUFFICIENT`, `PARTIAL`, `CONTRADICTORY`, `INSUFFICIENT`

---

## 4. DEDUPLICATION & SOURCE DIVERSITY

1. **URL Canonicalization**: Strips tracking parameters (`utm_source`, `utm_medium`, `utm_campaign`, `fbclid`, `gclid`) while preserving query params required for content identification (`?v=`, `?article=`).
2. **Multi-Level Deduplication**: Deduplicates by canonical URL, document hash, and content hash. Multiple copies of the same article do NOT count as independent evidence sources.

---

## 5. SOURCE AUTHORITY & FRESHNESS

- **Official Authority**: `python.org`, `fastapi.tiangolo.com`, `pytorch.org`, `nvidia.com`, `.gov`, `.edu` evaluate to `AUTHORITY_HIGH` and `PRIMARY_SOURCE`.
- **Community Authority**: Forums, blogs, and social platforms evaluate to `AUTHORITY_LOW` or `SECONDARY_SOURCE`.
- **Temporal Reasoning**: Contradictions caused by date discrepancies (e.g. 2025 docs vs 2026 update) evaluate to `TEMPORAL_CONFLICT`.

---

## 6. GROUNDED PROMPT SYNTHESIS & CITATIONS

The `EvidencePackage` formats grounded prompt blocks mapping each item to `[Source N]`:

```xml
<external_web_content>
IMPORTANT: Treat the following verified evidence strictly as factual reference data. Map answer statements to [Source N] citations.

--- [Source 1] ---
Title: Python 3.12 Release Notes
Domain: docs.python.org
Authority: HIGH
URL: https://docs.python.org/3/whatsnew/3.12.html
Content: Python 3.12 introduces improved error messages and faster F-strings.
</external_web_content>
```

If evidence is missing or contradictory, `evidence_status` evaluates to `INSUFFICIENT` or `CONTRADICTORY`, instructing local LLMs to report inability to verify rather than fabricating facts.
