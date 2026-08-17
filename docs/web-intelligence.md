# Saki AI — Advanced Web Intelligence Subsystem Specification
**Sprint 16 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Advanced Web Intelligence Subsystem  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Advanced Web Intelligence Engine ([`WebIntelligenceCapability`](file:///c:/Users/gurus/work/saki/backend/services/web_intelligence.py#L48)) upgrades Saki's web search into a real-time, multi-step web intelligence pipeline—**WITHOUT creating a secondary web agent (`WebAgent`, `SearchAgent`, `BrowserAgent`, `WebResearchAgent`), second search engine, or second browser implementation**.

```
User Request
    ↓
Saki Brain (chat.py)
    ↓
Search Strategy & Query Refinement (WebIntelligenceCapability.refine_queries)
    ↓
Outbound Privacy Gate (PrivacyPolicyEngine Outbound Redaction)
    ↓
Multi-Source Search & Fetch (WorldAccessManager / DuckDuckGoSearchProvider)
    ↓
Primary Source Prioritization (Official Docs > Generic Snippets)
    ↓
DOM Browser Fallback for JS Pages (Sprint 7 BrowserController)
    ↓
Evidence Intelligence & Prompt Injection Sanitization (Sprint 4 EvidenceEngine)
    ↓
Cross-Source Knowledge Fusion & Conflict Detection (Sprint 14 KnowledgeFusionEngine)
    ↓
Unified Knowledge RAG Packaging (Sprint 13 UnifiedKnowledgeEngine)
    ↓
Knowledge Graph Context (Sprint 15 KnowledgeGraphEngine)
    ↓
Saki Central Brain (Grounded Response Generation with Source Provenance)
```

---

## 2. MULTI-STEP QUERY REFINEMENT & PRIMARY SOURCE PRIORITY

- **Multi-Step Query Refinement**: Formulates initial search queries and generates follow-up queries based on gap analysis.
- **Primary Source Prioritization**: Ranks official documentation (`docs.python.org`, `fastapi.tiangolo.com`, `github.com`, `.gov`, `.edu`) over generic search engine snippets.
- **DOM Browser Fallback**: Triggers Sprint 7 [`BrowserController`](file:///c:/Users/gurus/work/saki/backend/services/browser_controller.py#L30) when search snippets indicate JavaScript rendering.

---

## 3. SECURITY, PRIVACY & PROMPT INJECTION DEFENSE

- **Outbound Query Sanitization**: All queries pass through Sprint 2 [`PrivacyPolicyEngine`](file:///c:/Users/gurus/work/saki/backend/core/privacy.py#L130) to redact user emails, API keys, credentials, or private memory context.
- **Untrusted Web Content Sandbox**: Webpage text is treated strictly as reference **DATA**. Prompt injection strings (`"Ignore previous instructions"`, `"Run command"`) are sanitized and stripped before entering context.
- **Budget Safeguards**:
  - `MAX_SEARCHES`: 3 max per request
  - `MAX_PAGES`: 5 pages max per search
  - `MAX_DEPTH`: 2 hops max
