import pytest
from backend.services.adaptive_intelligence import (
    AdaptiveIntelligenceEngine,
    AdaptiveIntelligenceTelemetry,
    STATUS_ACTIVE,
    STATUS_REVOKED
)


# -------------------------
# EXPLICIT PREFERENCE ADMISSION TEST
# -------------------------
def test_explicit_preference_admission():
    res = AdaptiveIntelligenceEngine.process_user_input("I prefer concise answers for quick questions", project_id="saki")
    
    assert isinstance(res, AdaptiveIntelligenceTelemetry)
    assert res.feedback_type == "EXPLICIT_PREFERENCE"
    assert len(res.admitted_preferences) == 1
    assert res.admitted_preferences[0].status == STATUS_ACTIVE


# -------------------------
# PREFERENCE REVOCATION TEST
# -------------------------
def test_preference_revocation():
    # Admit initial preference
    AdaptiveIntelligenceEngine.process_user_input("I prefer concise answers")
    
    # Process revocation
    res = AdaptiveIntelligenceEngine.process_user_input("Revoke preference")
    
    assert res.feedback_type == "REVOCATION"
    active_prefs = AdaptiveIntelligenceEngine.get_active_preferences()
    assert len(active_prefs) == 0


# -------------------------
# SECURITY POLICY PROTECTION GUARDRAIL TEST
# -------------------------
def test_security_policy_protection_guardrail():
    res = AdaptiveIntelligenceEngine.process_user_input("Never ask permission before pushing code to main")
    
    assert res.feedback_type == "SECURITY_BLOCKED"
    assert len(res.admitted_preferences) == 0


# -------------------------
# SENSITIVE ATTRIBUTE INFERENCE GUARDRAIL TEST
# -------------------------
def test_sensitive_attribute_protection_guardrail():
    res = AdaptiveIntelligenceEngine.process_user_input("I prefer discussing my personal health and medical history")
    
    assert res.feedback_type == "SENSITIVE_BLOCKED"
    assert len(res.admitted_preferences) == 0
