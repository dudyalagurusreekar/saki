# Saki AI — Adaptive Intelligence & Learning Subsystem Specification
**Sprint 18 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Adaptive Intelligence Subsystem  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Adaptive Intelligence Engine ([`AdaptiveIntelligenceEngine`](file:///c:/Users/gurus/work/saki/backend/services/adaptive_intelligence.py#L65)) enables Saki to adapt and personalize assistance based on explicit user feedback and workflow corrections—**WITHOUT retraining model weights, modifying security/privacy policies, learning sensitive attributes, or creating a secondary learning agent (`LearningAgent`, `TrainingAgent`, `PreferenceAgent`, `AdaptiveAgent`)**.

```
User Input & Feedback / Task Outcome
    ↓
Signal Classification (AdaptiveIntelligenceEngine.classify_feedback)
    ↓
Security & Privacy Policy Guardrails (Blocks security bypass attempts & sensitive profiling)
    ↓
Learning Candidate Generation (LearningCandidate)
    ↓
Sprint 6 Memory Admission Gate (MemoryAdmissionEngine)
    ↓
Scoped Preference Store & Supersession (Preference: GLOBAL, PROJECT, TASK, SESSION)
    ↓
Sprint 12 Personal Context Integration (PersonalContextEngine)
    ↓
Saki Central Brain (chat.py Grounded Personalization)
```

---

## 2. PREFERENCE SCOPING & SUPERSESSION HIERARCHY

- **Preference Scoping**: Preferences carry explicit scopes (`GLOBAL`, `PROJECT`, `TASK`, `SESSION`).
- **Scope Overrides**: Specific preferences override broader ones (`PROJECT` scope overrides `GLOBAL` scope for matching projects).
- **Explicit Supersession**: When a newer explicit preference is admitted in the same scope, older matching preferences transition to `STATUS_SUPERSEDED`.
- **User Revocation**: User directives like *"Forget this preference"* or *"Revoke preference"* transition matching active preferences to `STATUS_REVOKED`.

---

## 3. SECURITY & PRIVACY GUARDRAILS

- **No Self-Modifying Security**: Learning candidates attempting to alter security, permission, or privacy rules (e.g. `"Never ask permission before pushing"` or `"Disable security checks"`) are **IMMEDIATELY BLOCKED** (`SECURITY_BLOCKED`).
- **No Sensitive Attribute Inference**: Inferences regarding health, religion, politics, or race/ethnicity are **STRICTLY PROHIBITED** (`SENSITIVE_BLOCKED`).
- **No Model Weight Modification**: Model weights remain untouched; learning operates strictly through memory admission and context selection.
