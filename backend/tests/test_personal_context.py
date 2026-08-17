import pytest
from backend.services.personal_context import (
    PersonalContextEngine,
    PersonalContextItem,
    AttentionPolicy,
    CAT_GOAL,
    CAT_PROJECT,
    CAT_PREFERENCE,
    SOURCE_USER_EXPLICIT,
    SOURCE_DERIVED,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    IMPORTANCE_HIGH,
    STATUS_ACTIVE,
    STATUS_SUPERSEDED,
    STATUS_REVOKED,
    MODE_SHOULD_NOTIFY,
    MODE_SHOULD_IGNORE
)



# -------------------------
# CONTEXT CLASSIFICATION & PROVENANCE TESTS
# -------------------------
def test_create_explicit_personal_context():
    item = PersonalContextItem(
        category=CAT_GOAL,
        content="Finish browser integration for Saki AI",
        source=SOURCE_USER_EXPLICIT
    )
    assert item.category == CAT_GOAL
    assert item.confidence == CONFIDENCE_HIGH
    assert item.status == STATUS_ACTIVE


def test_memory_poisoning_lowers_web_derived_confidence():
    item = PersonalContextItem(
        category=CAT_PREFERENCE,
        content="User prefers external framework X",
        source="WEB"
    )
    added = PersonalContextEngine.add_item(item)
    assert added.confidence == CONFIDENCE_LOW
    assert added.source == SOURCE_DERIVED


# -------------------------
# MINIMAL CONTEXT SELECTION TEST
# -------------------------
def test_minimal_context_selection_budget():
    item = PersonalContextItem(category=CAT_PROJECT, content="User is working on Saki AI project", importance=IMPORTANCE_HIGH)
    PersonalContextEngine.add_item(item)
    selected = PersonalContextEngine.select_minimal_context("Saki AI project")
    
    assert isinstance(selected, list)
    assert len(selected) <= 5
    assert any("Saki" in i.content for i in selected)



# -------------------------
# CONFLICT RESOLUTION & FORGET TESTS
# -------------------------
def test_context_conflict_resolution():
    item1 = PersonalContextItem(category=CAT_PROJECT, content="Working on Saki v1")
    PersonalContextEngine.add_item(item1)
    
    # Resolve conflict with new authoritative statement
    new_item = PersonalContextEngine.resolve_conflict(CAT_PROJECT, "Working on Saki v2")
    
    assert new_item.status == STATUS_ACTIVE
    assert item1.status == STATUS_SUPERSEDED


def test_user_controlled_forget():
    item = PersonalContextItem(category=CAT_PREFERENCE, content="Forget me test item")
    PersonalContextEngine.add_item(item)
    
    forgotten_count = PersonalContextEngine.forget_context("Forget me test")
    assert forgotten_count > 0
    assert item.status == STATUS_REVOKED


# -------------------------
# PROACTIVE ATTENTION POLICY TEST
# -------------------------
def test_attention_policy_evaluation():
    policy_normal = AttentionPolicy(proactive_level="NORMAL")
    mode = PersonalContextEngine.evaluate_proactive_attention(policy_normal, event_importance="HIGH")
    assert mode == MODE_SHOULD_NOTIFY

    policy_off = AttentionPolicy(proactive_level="OFF")
    mode_off = PersonalContextEngine.evaluate_proactive_attention(policy_off)
    assert mode_off == MODE_SHOULD_IGNORE
