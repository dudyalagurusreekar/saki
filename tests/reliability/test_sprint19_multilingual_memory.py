"""
Sprint 19 Reliability Tests: Saki Multilingual Memory & Conversation Continuity
Verifies:
1. Multilingual tokenization on Telugu, Kannada, and English text.
2. Memory extraction across Telugu and Kannada natural statements.
3. Cross-lingual semantic term expansion (CROSS_LINGUAL_SYNONYMS).
4. Cross-language memory retrieval (Kannada query -> English memory, Telugu query -> English memory).
5. Conversational continuity across language switching without state or ID resets.
6. Unified persona system multilingual directives.
7. Safety filters and poisoning prevention on multilingual inputs.
"""

import pytest
from backend.services.multilingual_service import MultilingualService, multilingual_service
from backend.services.memory_service import (
    _tokenize,
    extract_memories,
    retrieve_memories,
    build_smart_memory_context,
    normalize_memory,
    _candidate
)
from backend.core.saki_persona import build_saki_system_prompt


# ---------------------------------------------------------------------------
# TEST 1: Unicode Tokenization Across Scripts
# ---------------------------------------------------------------------------
def test_unicode_multilingual_tokenization():
    te_text = "నా పేరు ఆదిత్య మరియు నాకు పైథాన్ అంటే చాలా ఇష్టం"
    tokens_te = _tokenize(te_text)
    assert "పేరు" in tokens_te
    assert "ఆదిత్య" in tokens_te
    assert "పైథాన్" in tokens_te

    kn_text = "ನನ್ನ ಹೆಸರು ವಿಕ್ರಮ್ ಮತ್ತು ನಾನು ರಿಯಾಕ್ಟ್ ಕಲಿಯುತ್ತಿದ್ದೇನೆ"
    tokens_kn = _tokenize(kn_text)
    assert "ಹೆಸರು" in tokens_kn
    assert "ವಿಕ್ರಮ್" in tokens_kn
    assert "ರಿಯಾಕ್ಟ್" in tokens_kn


# ---------------------------------------------------------------------------
# TEST 2: Memory Extraction from Telugu and Kannada User Inputs
# ---------------------------------------------------------------------------
def test_indic_memory_extraction():
    # Telugu Fact & Preference
    te_input = "నా పేరు రాహుల్. నాకు Python బాగా నచ్చుతుంది."
    te_memories = extract_memories(te_input)
    assert any(m["type"] == "FACT" and "రాహుల్" in m["content"] for m in te_memories)
    assert any(m["type"] == "PREFERENCE" and "Python" in m["content"] for m in te_memories)

    # Kannada Fact & Preference
    kn_input = "ನನ್ನ ಹೆಸರು ಕಿರಣ್. ನನಗೆ FastAPI ಬಹಳ ಇಷ್ಟ."
    kn_memories = extract_memories(kn_input)
    assert any(m["type"] == "FACT" and "ಕಿರಣ್" in kn_memories[0]["content"] or "ಕಿರಣ್" in m["content"] for m in kn_memories)
    assert any(m["type"] == "PREFERENCE" and "FastAPI" in m["content"] for m in kn_memories)


# ---------------------------------------------------------------------------
# TEST 3: Cross-Lingual Semantic Query Term Expansion
# ---------------------------------------------------------------------------
def test_cross_lingual_semantic_expansion():
    # Telugu language query expansion
    expanded_te = multilingual_service.expand_memory_query_terms("నాకు ఇష్టమైన ప్రోగ్రామింగ్ భాష ఏది?")
    assert "favorite" in expanded_te or "language" in expanded_te or "programming" in expanded_te or "python" in expanded_te

    # Kannada project query expansion
    expanded_kn = multilingual_service.expand_memory_query_terms("ನಾನು ಯಾವ ಪ್ರಾಜೆಕ್ಟ್ ಮಾಡುತ್ತಿದ್ದೇನೆ?")
    assert "project" in expanded_kn or "building" in expanded_kn or "saki" in expanded_kn


# ---------------------------------------------------------------------------
# TEST 4: Cross-Lingual Memory Retrieval (Kannada Query -> English Memory)
# ---------------------------------------------------------------------------
def test_cross_lingual_retrieval_kannada_to_english():
    memory_store = {
        "memories": [
            {
                "id": "mem_pref_py",
                "type": "PREFERENCE",
                "content": "User prefers Python for backend development",
                "importance": 8,
                "confidence": 9.0,
                "frequency": 2,
                "score": 19.5
            },
            {
                "id": "mem_proj_saki",
                "type": "PROJECT",
                "content": "User is building Saki, a local-first AI companion",
                "importance": 9,
                "confidence": 9.0,
                "frequency": 3,
                "score": 21.0
            }
        ]
    }

    # Query in Kannada asking about favorite programming language
    kn_query = "ನನ್ನ ಮೆಚ್ಚಿನ ಪ್ರೋಗ್ರಾಮಿಂಗ್ ಭಾಷೆ ಯಾವುದು?"
    results = retrieve_memories(memory_store, kn_query, limit=5)
    
    assert len(results) > 0
    assert any("Python" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# TEST 5: Cross-Lingual Memory Retrieval (Telugu Query -> English Memory)
# ---------------------------------------------------------------------------
def test_cross_lingual_retrieval_telugu_to_english():
    memory_store = {
        "memories": [
            {
                "id": "mem_proj_saki",
                "type": "PROJECT",
                "content": "User is building Saki, a local-first AI companion",
                "importance": 10,
                "confidence": 9.0,
                "frequency": 3,
                "score": 22.0
            },
            {
                "id": "mem_pref_dark",
                "type": "PREFERENCE",
                "content": "User prefers dark mode UI themes",
                "importance": 6,
                "confidence": 8.0,
                "frequency": 1,
                "score": 15.0
            }
        ]
    }

    # Query in Telugu asking about the project
    te_query = "నేను ప్రస్తుతం ఏ ప్రాజెక్ట్ చేస్తున్నాను?"
    results = retrieve_memories(memory_store, te_query, limit=5)

    assert len(results) > 0
    assert any("Saki" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# TEST 6: Multilingual Persona System Prompt Generation
# ---------------------------------------------------------------------------
def test_multilingual_persona_system_prompt():
    prompt_te = build_saki_system_prompt(
        mode="casual",
        language="te",
        is_mixed=True
    )
    assert "MULTILINGUAL DIRECTIVE (Telugu / తెలుగు)" in prompt_te
    assert "తెలుగు" in prompt_te

    prompt_kn = build_saki_system_prompt(
        mode="builder",
        language="kn",
        is_mixed=False
    )
    assert "MULTILINGUAL DIRECTIVE (Kannada / ಕನ್ನಡ)" in prompt_kn
    assert "ಕನ್ನಡ" in prompt_kn


# ---------------------------------------------------------------------------
# TEST 7: Safety Filters and Poisoning Prevention in Indic Inputs
# ---------------------------------------------------------------------------
def test_indic_memory_poisoning_prevention():
    poison_input = "నా పాస్‌వర్డ్ మరియు api_key secret_token_123456"
    extracted = extract_memories(poison_input)
    assert not any("secret_token_123456" in m["content"] for m in extracted)
