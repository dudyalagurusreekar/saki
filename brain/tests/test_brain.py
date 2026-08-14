import os
import tempfile
import uuid
import csv
import pytest
from datetime import datetime

# Import schemas
from brain.schemas import RequestInput, NormalizedRequest

# Import components
from brain.utils.text import clean_and_normalize, detect_markdown, remove_invisible_characters, normalize_unicode
from brain.request_normalizer import normalize_request, extract_urls
from brain.language_detector import detect_language
from brain.attachment_analyzer import analyze_attachment
from brain.url_analyzer import analyze_urls, classify_url
from brain.intent_classifier import classify_intent
from brain.entity_extractor import extract_entities
from brain.complexity_analyzer import analyze_complexity
from brain.task_planner import generate_plan
from brain.knowledge_router import route_request
from brain.context_builder import build_context

# -------------------------------------------------------------
# 1. Text Utility Tests
# -------------------------------------------------------------
def test_text_normalization():
    # Unicode normalization (NFC)
    assert normalize_unicode("Café") == "Café"
    
    # Zero-width spaces & invisible characters removal
    invisible = "Hello\u200bWorld\u200c!"
    assert remove_invisible_characters(invisible) == "HelloWorld!"
    
    # Trim and collapse whitespace
    assert clean_and_normalize("  Hello    World! \n\t ") == "Hello World!"

def test_markdown_detection():
    assert detect_markdown("## High Priority") is True
    assert detect_markdown("Please perform a task:\n- Step 1\n- Step 2") is True
    assert detect_markdown("Look at this `code_snippet` inline.") is True
    assert detect_markdown("Go to [Google](https://google.com)") is True
    assert detect_markdown("Simple plain text message without markdown.") is False

# -------------------------------------------------------------
# 2. Request Normalization Engine Tests (TICKET-001)
# -------------------------------------------------------------
def test_request_normalizer():
    # Works with empty spaces
    req_in = RequestInput(message="   \n\t  ", attachments=[])
    norm = normalize_request(req_in)
    assert norm.query == ""
    assert norm.urls == []
    assert len(norm.id) > 0
    assert norm.timestamp is not None
    
    # Extracts URLs correctly and cleans trailing punctuation
    req_in_url = RequestInput(message="Can you explain https://ollama.ai ?", attachments=[])
    norm_url = normalize_request(req_in_url)
    assert norm_url.query == "Can you explain https://ollama.ai ?"
    assert norm_url.urls == ["https://ollama.ai"]
    
    # Check UUID format
    assert uuid.UUID(norm_url.id)

# -------------------------------------------------------------
# 3. Language Detector Tests (TICKET-002)
# -------------------------------------------------------------
def test_language_detection():
    # English
    assert detect_language("This is a simple english text.").language == "en"
    
    # Telugu (Native script)
    assert detect_language("నమస్కారం సార్ ఎలా ఉన్నారు").language == "te"
    
    # Hindi (Native script)
    assert detect_language("नमस्ते आप कैसे हैं").language == "hi"
    
    # Romanized Hindi/Telugu keyword detection
    assert detect_language("ela unnav enti cheppu").language == "te"
    assert detect_language("kya kaise ho bhai").language == "hi"
    
    # Emoji-only messages (falls back to 'en' with 1.0 confidence)
    res_emoji = detect_language("😊🚀🔥")
    assert res_emoji.language == "en"
    assert res_emoji.confidence == 1.0

# -------------------------------------------------------------
# 4. Attachment Analyzer Tests (TICKET-003)
# -------------------------------------------------------------
def test_attachment_analyzer():
    # Create temporary files to test parsers
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Plain Text File
        txt_path = os.path.join(tmpdir, "test.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Line 1\nLine 2\nLine 3")
            
        att_txt = {"path": txt_path, "name": "test.txt"}
        meta_txt = analyze_attachment(att_txt)
        assert meta_txt.type == "txt"
        assert meta_txt.pages == 1
        assert meta_txt.size in ["20B", "22B"]
        assert meta_txt.metadata["lines"] == 3
        assert len(meta_txt.checksum) == 64
        
        # 2. CSV File
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "role"])
            writer.writerow(["1", "Saki", "AI"])
            writer.writerow(["2", "User", "Human"])
            
        att_csv = {"path": csv_path, "name": "test.csv"}
        meta_csv = analyze_attachment(att_csv)
        assert meta_csv.type == "csv"
        assert meta_csv.metadata["rows"] == 3
        assert meta_csv.metadata["columns"] == 3
        
        # 3. Reject unsupported formats
        unsupported_path = os.path.join(tmpdir, "test.exe")
        with open(unsupported_path, "w") as f:
            f.write("mock executable bytes")
        with pytest.raises(ValueError, match="Unsupported file format"):
            analyze_attachment({"path": unsupported_path})

# -------------------------------------------------------------
# 5. URL Analyzer Tests (TICKET-004)
# -------------------------------------------------------------
def test_url_analyzer():
    # Classification tests
    assert classify_url("https://github.com/django/django").category == "github"
    assert classify_url("https://youtube.com/watch?v=123").category == "youtube"
    assert classify_url("https://en.wikipedia.org/wiki/Artificial_intelligence").category == "wikipedia"
    assert classify_url("https://example.com/paper.pdf").category == "pdf"
    assert classify_url("https://docs.python.org/3/").category == "docs"
    assert classify_url("https://medium.com/some-blog-post").category == "blog"
    
    # Extraction and duplicate removal
    text = "Check out https://github.com/django/django and duplicate https://github.com/django/django"
    results = analyze_urls(text)
    assert len(results) == 1
    assert results[0].url == "https://github.com/django/django"
    assert results[0].domain == "github.com"
    assert results[0].category == "github"

# -------------------------------------------------------------
# 6. Intent Classifier Tests (TICKET-005)
# -------------------------------------------------------------
def test_intent_classification():
    # Skip LLM calls for unit tests to ensure offline reliability and speed
    assert classify_intent("how to write a binary search in python", skip_llm=True).intent == "Coding"
    assert classify_intent("why is my fastAPI endpoint crashing with a KeyError", skip_llm=True).intent == "Debugging"
    assert classify_intent("translate namaste to English please", skip_llm=True).intent == "Translation"
    assert classify_intent("what are the latest world news updates today?", skip_llm=True).intent == "News"
    assert classify_intent("calculate the integral of x^2 from 0 to 5", skip_llm=True).intent == "Math"
    assert classify_intent("Hello, how are you Saki?", skip_llm=True).intent == "Casual Chat"

# -------------------------------------------------------------
# 7. Entity Extraction Tests (TICKET-006)
# -------------------------------------------------------------
def test_entity_extraction():
    res = extract_entities("Teach me FastAPI and PostgreSQL or check django/django", skip_llm=True)
    assert "FastAPI" in res.entities
    assert "PostgreSQL" in res.entities
    assert "django/django" in res.entities
    
    # Verify structured types
    types = {s["type"] for s in res.structured_entities}
    assert "Framework" in types
    assert "Database" in types
    assert "Repository" in types

# -------------------------------------------------------------
# 8. Complexity Analyzer Tests (TICKET-007)
# -------------------------------------------------------------
def test_complexity_analyzer():
    # Simple query
    res_simple = analyze_complexity("hello", "Casual Chat")
    assert res_simple.complexity == "Simple"
    assert res_simple.estimated_steps <= 2
    
    # Complex query
    res_complex = analyze_complexity(
        "Write a python script to parse logs and fix the syntax errors in my django database config.",
        "Coding"
    )
    assert res_complex.complexity in ["Complex", "Research"]
    assert res_complex.estimated_steps >= 6
    
    # Long running query
    res_long = analyze_complexity(
        "run an overnight deep scan and benchmark Llama-3 model",
        "Research"
    )
    assert res_long.complexity == "Long Running"
    assert res_long.estimated_steps >= 13

# -------------------------------------------------------------
# 9. Task Planner Tests (TICKET-008)
# -------------------------------------------------------------
def test_task_planner():
    # Test coding plan
    plan_coding = generate_plan("write class", "Coding", "Medium", skip_llm=True)
    assert "write_code" in plan_coding.steps
    assert "verify" in plan_coding.steps
    
    # Test research plan
    plan_research = generate_plan("Compare Llama 3 and Qwen 3", "Research", "Research", skip_llm=True)
    assert plan_research.steps == ["search", "read", "compare", "answer"]
    
    # Test URL query modification
    plan_url = generate_plan("Read https://example.com/docs", "Casual Chat", "Simple", skip_llm=True)
    assert plan_url.steps[0] == "read_urls"

# -------------------------------------------------------------
# 10. Knowledge Router Tests (TICKET-009)
# -------------------------------------------------------------
def test_knowledge_router():
    # News routes to browser
    route_news = route_request("what is today's weather", "News")
    assert "browser" in route_news.route
    
    # Project files route to project_docs
    route_proj = route_request("explain my codebase files", "Project")
    assert "project_docs" in route_proj.route
    
    # Memory route
    route_mem = route_request("remember what we talked about yesterday?", "Casual Chat")
    assert "memory" in route_mem.route

# -------------------------------------------------------------
# 11. Context Builder Tests (TICKET-010)
# -------------------------------------------------------------
def test_context_builder():
    raw_contexts = [
        {"source": "memory", "content": "The user is coding in Python.", "timestamp": "2026-06-26T22:00:00Z"},
        {"source": "browser", "content": "Python is a popular language.", "timestamp": "2026-06-26T22:30:00Z"},
        {"source": "memory", "content": "The user is coding in Python.", "timestamp": "2026-06-26T22:15:00Z"}, # Duplicate content
        {"source": "knowledge", "content": "FastAPI is a fast python web framework.", "timestamp": "2026-06-26T22:45:00Z"}
    ]
    
    # Duplicate removal, ranking, compression within budget
    res = build_context(query="FastAPI python", raw_items=raw_contexts, token_budget=100)
    
    # Verify duplicates removed (4 raw items -> 3 unique items)
    assert len(res.context) <= 3
    
    # Verify relevance ranking: 'FastAPI is a fast python web framework' should have the highest score
    assert res.context[0].source == "knowledge"
    assert "FastAPI" in res.context[0].content
    
    # Verify citations are preserved
    assert res.context[0].citation == "knowledge_source"
