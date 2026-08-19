# SPRINT 5 FINAL REPORT: SAKI ENTITY RESOLUTION & SEMANTIC RELEVANCE

**Repository**: `https://github.com/dudyalagurusreekar/saki`  
**Branch**: `p1`  
**Date**: August 18, 2026  
**Status**: **COMPLETED (37 / 37 Reliability Tests Passing, 100% Success)**

---

## 1. Previous Relevance Architecture vs New Relevance Architecture

### 1.1 Previous Architecture (Sprint 0–4 Baseline)
In the previous pipeline, relevance evaluation was primarily keyword-based:
- Search results were split into tokens. If any word in the user's query appeared in the search snippet (e.g. `"Vijayawada"`), the result was classified as `RELEVANT`.
- **Failure Mode**: When asking for `"special food in Vijayawada"`, articles on the *history of Vijayawada* or the *weather in Vijayawada* matched the keyword `"Vijayawada"` and were passed directly to the model as verified food evidence.
- Similarly, for `"latest FastAPI version"`, generic introductory tutorials (e.g. *"FastAPI is a modern Python web framework..."*) matched the keyword `"FastAPI"` and were treated as sufficient evidence despite containing no version numbers.
- **Root Vulnerability**: `KEYWORD MATCH ≠ RELEVANCE` and `RELATED ≠ SUFFICIENT`.

```
[User Query] ──> [Naive Keyword Search] ──> [All "Vijayawada" Matches Marked RELEVANT] ──> [Noisy Context]
```

### 1.2 New Semantic Relevance Architecture (Sprint 5)
Sprint 5 introduces a multi-signal, layered semantic relevance pipeline:
1. **Query Understanding Layer (`QueryUnderstanding`)**: Structured semantic extraction separating entity, entity type, topic, intent, location, temporal scope, and requested information.
2. **Intent-Preserving Search Optimization**: Reformulating raw user queries into targeted search expressions (e.g. `"special food traditional dishes Vijayawada"` instead of just `"Vijayawada"`).
3. **Multi-Signal Semantic Relevance Gate (`RelevanceGate`)**: Evaluates retrieved sources against 5 independent signals:
   - Entity Alignment (25%)
   - Topic Alignment & Negative Collision Guard (30%)
   - Intent Alignment (15%)
   - Location Alignment (15%)
   - Coverage / Sufficiency Score (15%)
4. **Sufficiency & Anti-Collision Guards**:
   - Negative topic collisions (e.g., weather or history content when food was asked) are penalized severely (`score <= 0.25`, `IRRELEVANT`).
   - Generic introductory content lacking version release payloads for version queries is classified as `IRRELEVANT` / `INSUFFICIENT` (`coverage < 0.30`).
5. **Explainable Diagnostic Telemetry**: Every candidate result receives an explainable `relevance_score` (0.0 to 1.0), `relevance_state` (`RELEVANT`, `IRRELEVANT`, `UNCERTAIN`), and `relevance_reason`.

```
[User Query]
     ↓
[QueryUnderstanding] (Entity, Location, Topic, Intent, Temporal, Required Info)
     ↓
[Search Query Reformulation] (e.g., "special food traditional dishes Vijayawada")
     ↓
[Multi-Signal Relevance Gate] ──> Entity Alignment (25%)
                               ├── Topic Alignment & Anti-Collision (30%)
                               ├── Intent Alignment (15%)
                               ├── Location Alignment (15%)
                               └── Sufficiency / Coverage Score (15%)
     ↓
[Filtered Evidence Package] (Only verified RELEVANT & SUFFICIENT sources synthesized into claims)
     ↓
[Final Model Prompt]
```

---

## 2. Structured Query Understanding Model

Defined in [`backend/services/action_engine.py`](file:///c:/Users/gurus/work/saki/backend/services/action_engine.py):

```python
class QueryUnderstanding(BaseModel):
    original_query: str = Field(default="")
    normalized_query: str = Field(default="")
    primary_entity: Optional[str] = Field(default=None)
    entity_type: Optional[str] = Field(default=None, description="location, software, concept, media, hardware, general, ambiguous")
    location: Optional[str] = Field(default=None)
    topic: Optional[str] = Field(default=None, description="food, tourism, weather, history, software_version, software_framework, movies, news, casual, concept")
    intent: Optional[str] = Field(default=None, description="recommendation, factual_lookup, explanation, live_update, version_query, casual_chat")
    temporal_requirement: str = Field(default=FRESHNESS_STABLE)
    recommendation_requirement: bool = Field(default=False)
    required_information: Optional[str] = Field(default=None)
    is_ambiguous: bool = Field(default=False)
    search_query_optimized: Optional[str] = Field(default=None)
```

---

## 3. Entity & Intent Extraction

### 3.1 Entity Extraction & Entity-Location Separation
- **Location Entities**: `Vijayawada`, `Hyderabad`, `Bengaluru`, `Chennai`, `Delhi`, `Mumbai`, `Kolkata`, `Visakhapatnam`, `Tirupati`, `Guntur`, `Anantapur`, `Tadipatri`, `Kambadur`, `Lepakshi`, `Andhra Pradesh`, `India`.
- **Software / Tech Entities**: `FastAPI`, `Python`, `Node.js`, `Ollama`, `React`, `PyTorch`, `Docker`, `Pydantic`, `Next.js`, `PostgreSQL`, `NVIDIA GPU`.
- **Media Entities**: `movies`, `films`.
- **Location vs Topic Distinction**:
  - Query: `"special food in Vijayawada"` $\rightarrow$ `location = "Vijayawada"`, `primary_entity = "Vijayawada"`, `topic = "food"`, `intent = "recommendation"`.
  - Query: `"weather in Vijayawada"` $\rightarrow$ `location = "Vijayawada"`, `primary_entity = "Vijayawada"`, `topic = "weather"`, `intent = "live_update"`.
  - Query: `"history of Vijayawada"` $\rightarrow$ `location = "Vijayawada"`, `primary_entity = "Vijayawada"`, `topic = "history"`, `intent = "factual_lookup"`.

### 3.2 Entity Ambiguity Handling (Part 9)
Single-word queries or queries without disambiguating domain context (e.g. `"tell me about Saki"`, `"tell me about Gemini"`) are flagged with `is_ambiguous = True` and `entity_type = "ambiguous"`. The system responds conversationally and requests clarification rather than hallucinating an arbitrary domain entity.

---

## 4. Multi-Signal Semantic Relevance Scoring Formula

Defined in [`backend/services/evidence_engine.py`](file:///c:/Users/gurus/work/saki/backend/services/evidence_engine.py):

$$\text{relevance\_score} = 0.25 \cdot \text{entity\_score} + 0.30 \cdot \text{topic\_score} + 0.15 \cdot \text{intent\_score} + 0.15 \cdot \text{location\_score} + 0.15 \cdot \text{coverage\_score}$$

### Decision Thresholds:
- **`RELEVANT`**: $\text{relevance\_score} \ge 0.55$
- **`UNCERTAIN`**: $0.35 \le \text{relevance\_score} < 0.55$ (resolved via deterministic fallback or local LLM adjudication; fails closed if unresolved)
- **`IRRELEVANT`**: $\text{relevance\_score} < 0.35$

### Strict Penalty Guards:
1. **Negative Collision Guard**: If query topic is `food` and the search result discusses `weather` or `history` without food vocabulary, `topic_score = 0.0` and `relevance_score` is hard-capped at $0.25$ (`IRRELEVANT`).
2. **Sufficiency Guard (`RELATED != SUFFICIENT`)**: For `software_version` queries, if the search result is an introductory overview lacking version strings or release statements, `coverage_score < 0.30` and `relevance_score` is hard-capped at $0.25$ (`IRRELEVANT`).
3. **Temporal Anchor Guard**: For queries requesting `2026`, results discussing older decades (e.g. 1970s) without the 2026 anchor are capped at $0.25$ (`IRRELEVANT`).

---

## 5. Search Query Quality Improvements (Part 12)

The system automatically refines external search queries based on `QueryUnderstanding`:

| Original User Query | Reformulated Search Query | Rationale |
| :--- | :--- | :--- |
| `"special food in Vijayawada"` | `"special food traditional dishes Vijayawada"` | Focuses retrieval on culinary specialties and prevents generic city overviews. |
| `"best places to visit in Vijayawada"` | `"best places to visit tourist attractions Vijayawada"` | Anchors retrieval on tourist spots and sightseeing landmarks. |
| `"weather in Vijayawada"` | `"current weather live forecast Vijayawada"` | Pulls live meteorological data rather than climate history. |
| `"history of Vijayawada"` | `"history historical heritage Vijayawada"` | Focuses on ancient dynasties and heritage monuments. |
| `"latest FastAPI version"` | `"latest FastAPI version official release"` | Targets PyPI/GitHub release notes and tags. |
| `"good movies in 2026"` | `"best movies in 2026 top rated film releases"` | Targets 2026 film release schedules and ratings. |

---

## 6. Automated Regression Test Suite Results

Run command:
```powershell
$env:PYTHONPATH="."; .\venv\Scripts\pytest tests/reliability/test_sprint5_relevance.py tests/reliability/test_sprint4_forensics.py tests/reliability/test_sprint3_current_info.py tests/reliability/test_sprint1_web_activation.py -v
```

### Test Breakdown:
| Test Suite | Total Tests | Passed | Failed | Status |
| :--- | :---: | :---: | :---: | :---: |
| **`test_sprint5_relevance.py` (Sprint 5)** | 8 | 8 | 0 | **PASS (100%)** |
| **`test_sprint4_forensics.py` (Sprint 4)** | 7 | 7 | 0 | **PASS (100%)** |
| **`test_sprint3_current_info.py` (Sprint 3)** | 11 | 11 | 0 | **PASS (100%)** |
| **`test_sprint1_web_activation.py` (Sprint 1)** | 11 | 11 | 0 | **PASS (100%)** |
| **Combined Reliability Matrix** | **37** | **37** | **0** | **PASS (100%)** |

### Detailed Sprint 5 Test Cases:
1. `test_01_food_in_vijayawada_relevance_discrimination`: Food results accepted; history & weather rejected $\rightarrow$ **PASS**
2. `test_02_fastapi_version_related_vs_sufficient`: Version release accepted; generic overview rejected $\rightarrow$ **PASS**
3. `test_03_what_is_fastapi_static_knowledge_path`: Explanatory query routes to static knowledge (`web_required = False`) $\rightarrow$ **PASS**
4. `test_04_places_to_visit_in_vijayawada`: Tourism results accepted; weather rejected $\rightarrow$ **PASS**
5. `test_05_weather_in_vijayawada`: Weather accepted; restaurants rejected $\rightarrow$ **PASS**
6. `test_06_history_of_vijayawada`: History accepted; street food rejected $\rightarrow$ **PASS**
7. `test_07_movies_in_2026`: 2026 releases accepted; 1970s retrospective rejected $\rightarrow$ **PASS**
8. `test_08_ambiguous_entity_handling`: "Saki" and "Gemini" handled cautiously as ambiguous entities $\rightarrow$ **PASS**

---

## 7. Manual Test Matrix Results (Part 19)

Executed via [`tests/reliability/run_sprint5_manual_matrix.py`](file:///c:/Users/gurus/work/saki/tests/reliability/run_sprint5_manual_matrix.py) against live local models (`qwen3:8b`, `qwen2.5-coder:7b`, `phi3:latest`):

| ID | User Query | Primary Entity | Topic | Intent | Web Req. | Search Query Generated | Status |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- | :--- |
| **1** | "special food in Vijayawada" | Vijayawada | food | recommendation | **True** | `special food traditional dishes Vijayawada` | **PASS** |
| **2** | "famous dishes in Vijayawada" | Vijayawada | food | recommendation | **True** | `special food traditional dishes Vijayawada` | **PASS** |
| **3** | "places to visit in Vijayawada" | Vijayawada | tourism | recommendation | **True** | `best places to visit tourist attractions Vijayawada` | **PASS** |
| **4** | "history of Vijayawada" | Vijayawada | history | factual_lookup | **False** | `history historical heritage Vijayawada` | **PASS** |
| **5** | "weather in Vijayawada" | Vijayawada | weather | live_update | **True** | `current weather live forecast Vijayawada` | **PASS** |
| **6** | "latest FastAPI version" | FastAPI | software_version | version_query | **True** | `latest FastAPI version official release` | **PASS** |
| **7** | "latest Python version" | Python | software_version | version_query | **True** | `latest Python version official release` | **PASS** |
| **8** | "what is FastAPI" | FastAPI | software_framework | general_explanation | **False** | `FastAPI framework overview definition` | **PASS** |
| **9** | "good movies in 2026" | movies | movies | recommendation | **True** | `best movies in 2026 top rated film releases` | **PASS** |
| **10** | "best movies in 2026" | movies | movies | recommendation | **True** | `best movies in 2026 top rated film releases` | **PASS** |
| **11** | "tell me about Saki" | Saki (ambiguous) | None | None | **False** | `tell me about Saki` | **PASS** |
| **12** | "tell me about Python" | Python | None | None | **False** | `tell me about Python` | **PASS** |
| **13** | "tell me about Gemini" | Gemini (ambiguous) | None | None | **False** | `tell me about Gemini` | **PASS** |

---

## 8. False Positives & False Negatives Analysis

### 8.1 False Positives Mitigated:
- **Generic Software Documentation on Version Queries**: Previously, official docs homepages were scored as 0.95 relevant because they matched the library name. Now, they are scored with `coverage < 0.30` and classified as `IRRELEVANT` / `INSUFFICIENT` if they lack release version data.
- **Cross-Topic City Queries**: Searching for food in Vijayawada previously accepted historical articles about ancient rulers. The negative anti-collision guard drops cross-topic results from `RELEVANT` to `IRRELEVANT` ($score \le 0.25$).

### 8.2 False Negatives Prevented:
- **Culinary Synonyms**: Dishes described with regional culinary terminology (e.g. *Andhra spicy meals, punugulu, gongura, tiffin, delicacies*) are correctly matched via `TOPIC_VOCABULARIES["food"]` even if the exact keyword "special food" does not appear in the text.
- **Semantic Version Formats**: Version strings such as `v0.115.0`, `0.115.0`, `v2.0` are recognized via regex patterns as direct evidence support.

---

## 9. Deferred Verification Problems (Part 18 Boundary)

> [!NOTE]
> **Boundary Rule**: Relevance answers: *"Does this search result actually relate to the user's question and contain the requested topic/entity/intent?"*  
> It does **NOT** answer: *"Is every individual factual claim inside this source true?"*  
> Claim-level factual verification, cross-source contradiction resolution, and hallucination elimination on obscure entity attributes are preserved for **Sprint 6**.

---

## 10. End-to-End Forensic Trace Examples

### Example 1: Local Recommendation Discrimination
```
QUERY: "special food in Vijayawada"
├── QUERY UNDERSTANDING:
│   ├── Primary Entity: Vijayawada (entity_type: location)
│   ├── Location: Vijayawada
│   ├── Topic: food
│   ├── Intent: recommendation
│   └── Optimized Search Query: "special food traditional dishes Vijayawada"
├── SEARCH RETRIEVAL (Raw Results):
│   ├── Candidate 1: "Famous Foods of Vijayawada: Punugulu, Gongura pachadi, Andhra meals..."
│   └── Candidate 2: "History of Vijayawada: Ancient dynasties and rulers..."
├── RELEVANCE EVALUATION:
│   ├── Candidate 1: entity=1.0, topic=1.0, intent=0.95, location=1.0, coverage=0.95 ──> Score: 0.98 [RELEVANT]
│   └── Candidate 2: entity=1.0, topic=0.0 (anti-collision), location=1.0, coverage=0.05 ──> Score: 0.25 [IRRELEVANT]
├── EVIDENCE PACKAGE:
│   └── Claims Synthesized: 1 (Candidate 1 only; Candidate 2 excluded)
└── FINAL MODEL CONTEXT: Cleanly grounded with culinary data without city history noise.
```

### Example 2: Version Query Sufficiency (`RELATED != SUFFICIENT`)
```
QUERY: "latest FastAPI version"
├── QUERY UNDERSTANDING:
│   ├── Primary Entity: FastAPI (entity_type: software)
│   ├── Topic: software_version
│   ├── Intent: version_query
│   └── Optimized Search Query: "latest FastAPI version official release"
├── SEARCH RETRIEVAL:
│   ├── Candidate 1: "Release FastAPI 0.115.0 - tiangolo/fastapi GitHub release notes..."
│   └── Candidate 2: "FastAPI Tutorial: FastAPI is a modern, high-performance web framework..."
├── RELEVANCE EVALUATION:
│   ├── Candidate 1: entity=1.0, topic=1.0, intent=1.0, coverage=1.0 (version 0.115.0 found) ──> Score: 0.98 [RELEVANT]
│   └── Candidate 2: entity=1.0, topic=0.20, intent=0.20, coverage=0.15 (no version string) ──> Score: 0.25 [IRRELEVANT]
├── EVIDENCE PACKAGE:
│   └── Claims Synthesized: 1 (Release notes only; tutorial excluded)
└── FINAL MODEL CONTEXT: Passes exact version release data to final prompt.
```

### Example 3: Temporal Scope Discrimination
```
QUERY: "good movies in 2026"
├── QUERY UNDERSTANDING:
│   ├── Primary Entity: movies (entity_type: media)
│   ├── Topic: movies
│   ├── Intent: recommendation
│   ├── Temporal Requirement: CURRENT (2026)
│   └── Optimized Search Query: "best movies in 2026 top rated film releases"
├── SEARCH RETRIEVAL:
│   ├── Candidate 1: "Best Movies in 2026 - Top Rated Releases and Upcoming Film Reviews..."
│   └── Candidate 2: "A Retrospective on 1970s Classical Cinema Movements..."
├── RELEVANCE EVALUATION:
│   ├── Candidate 1: entity=1.0, topic=1.0, intent=1.0, temporal_match=1.0, coverage=1.0 ──> Score: 0.98 [RELEVANT]
│   └── Candidate 2: entity=0.60, topic=0.20, intent=0.15, temporal_match=0.0 (1970s) ──> Score: 0.25 [IRRELEVANT]
├── EVIDENCE PACKAGE:
│   └── Claims Synthesized: 1 (2026 movie list only; 1970s article rejected)
└── FINAL MODEL CONTEXT: Cleanly focused on 2026 film recommendations.
```

---

## 11. Sprint 5 Completion Checklist

- [x] Query entities identified correctly.
- [x] Query topic identified correctly.
- [x] User intent identified correctly.
- [x] Location relationships preserved (topic vs location).
- [x] Search queries reflect user intent (intent-preserving reformulation).
- [x] Keyword-only relevance eliminated as primary gate; replaced with multi-signal semantic scoring.
- [x] Relevant results retained.
- [x] Clearly irrelevant results rejected/down-ranked.
- [x] Related-but-insufficient results distinguishable (`RELATED != SUFFICIENT`).
- [x] Local queries distinguish food/history/weather/tourism for the same entity.
- [x] Version queries distinguish version release information from generic introductory documentation.
- [x] Recommendation queries retrieve recommendation-relevant sources.
- [x] Ambiguous entities handled cautiously without false assumptions.
- [x] Existing web pipeline remains unchanged architecturally.
- [x] Current-information behavior from Sprint 4 remains fully functional.
- [x] No duplicate search pipeline introduced.
- [x] All 37 automated tests passing (100% success).
- [x] All 13 manual test matrix queries evaluated and logged.

---

*Sprint 5 is complete. Per directives: STOP after Sprint 5. DO NOT start Sprint 6.*
