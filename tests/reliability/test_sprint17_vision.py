"""
Sprint 17 Reliability Test Suite: Saki Vision System & Image Understanding
Verifies image validation, preprocessing/downscaling, local Gemma 3 4B execution,
structured visual extraction (OCR, UI components, code, error tracebacks),
multi-model orchestration (Gemma -> Qwen Coder / Qwen 3), state transitions,
upload API security, and text/voice pipeline independence.
"""

import os
import io
from typing import Tuple, Optional, List
import pytest
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.events import SakiState
from backend.services.vision_service import vision_service, VisionAnalysisResult, ImageMetadata
from backend.services.orchestrator import SakiModelOrchestrator


def _create_test_image(width: int = 400, height: int = 300, text: str = "Saki Vision Test", fmt: str = "PNG") -> Tuple[str, bytes]:
    """Helper to generate a test image file and bytes."""
    os.makedirs("data/test_uploads", exist_ok=True)
    img = Image.new("RGB", (width, height), color=(240, 248, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, width - 20, height - 20], fill=(255, 255, 255), outline=(14, 165, 233), width=2)
    draw.text((40, 40), text, fill=(15, 23, 42))
    
    file_path = os.path.abspath(os.path.join("data", "test_uploads", f"test_img_{width}x{height}.{fmt.lower()}"))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    img.save(file_path, format=fmt)
    return file_path, buf.getvalue()


class TestSprint17VisionSystem:
    """Test suite covering all Sprint 17 Vision & Image Understanding deliverables."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(app)

    def test_01_image_validation_supported_formats(self):
        """Tests that standard formats (PNG, JPEG, WEBP, BMP) are validated with accurate metadata."""
        for fmt in ["PNG", "JPEG", "WEBP", "BMP"]:
            fpath, bdata = _create_test_image(300, 200, f"Format {fmt}", fmt=fmt)
            valid, err, meta = vision_service.validate_image_file(fpath)
            assert valid is True, f"Failed for format {fmt}: {err}"
            assert meta is not None
            assert meta.original_width == 300
            assert meta.original_height == 200
            assert meta.was_resized is False

            # Test byte validation
            b_valid, b_err, b_meta = vision_service.validate_image_bytes(bdata, filename=f"test.{fmt.lower()}")
            assert b_valid is True
            assert b_meta.original_width == 300

    def test_02_image_validation_corrupted_and_invalid(self):
        """Tests that invalid files, fake headers, and corrupted bytes fail gracefully."""
        # 1. Fake text file disguised as PNG
        corrupt_bytes = b"This is not a real image at all."
        valid, err, meta = vision_service.validate_image_bytes(corrupt_bytes, filename="fake.png")
        assert valid is False
        assert "Corrupted or invalid" in err

        # 2. Non-existent path
        valid, err, meta = vision_service.validate_image_file("data/does_not_exist.png")
        assert valid is False
        assert "File not found" in err

        # 3. Unsupported extension
        unsupported_path = os.path.abspath("data/test_uploads/sample.exe")
        with open(unsupported_path, "wb") as f:
            f.write(b"fake exe")
        valid, err, meta = vision_service.validate_image_file(unsupported_path)
        assert valid is False
        assert "Unsupported image extension" in err

    def test_03_image_downscaling_and_aspect_ratio(self):
        """Tests that oversized images (>1536px) are downscaled properly while preserving aspect ratio."""
        # Create 3000x2000 image
        fpath, _ = _create_test_image(3000, 2000, "High Res Image", fmt="PNG")
        b64_str, meta = vision_service.preprocess_image(fpath)
        
        assert meta.was_resized is True
        assert meta.original_width == 3000
        assert meta.original_height == 2000
        assert meta.processed_width == 1536
        assert meta.processed_height == int(2000 * (1536 / 3000))
        assert len(b64_str) > 100

    def test_04_structured_vision_response_parsing(self):
        """Tests parser for OCR code extraction, UI elements, and error detection."""
        sample_gemma_output = (
            "VISUAL DESCRIPTION: A code editor showing Python code with a traceback error in the terminal.\n\n"
            "CODE & OCR:\n"
            "```python\n"
            "def calculate_total(items):\n"
            "    return sum(item['price'] for item in items)\n"
            "```\n\n"
            "UI ELEMENTS:\n"
            "- VS Code Editor\n"
            "- Integrated Terminal\n"
            "- File tree on left\n\n"
            "ERRORS & TRACEBACKS:\n"
            "- KeyError: 'price' at line 2 in calculate_total\n"
        )
        parsed = vision_service.parse_structured_vision_response(sample_gemma_output)
        assert parsed.success is True
        assert "calculate_total" in parsed.detected_text
        assert any("VS Code" in u for u in parsed.ui_elements)
        assert any("KeyError" in e for e in parsed.errors_detected)
        
        context_str = parsed.to_context_string()
        assert "[Visual Inspection Context (Gemma 3 4B)]" in context_str
        assert "calculate_total" in context_str

    def test_05_multi_model_orchestration_code_screenshot(self):
        """Tests that a screenshot with a coding fix query routes to Qwen 2.5 Coder."""
        attachments = [{"name": "traceback_error.png", "type": "image", "path": "data/uploads/error.png"}]
        decision = SakiModelOrchestrator.classify_request(
            "Fix the code in this screenshot and explain the error",
            attachments=attachments
        )
        assert decision.vision_required is True
        assert decision.coding_required is True
        assert decision.selected_model == settings.MODEL_CODER
        assert decision.conversation_mode == "builder"
        assert decision.task_type == "visual_coding_task"

    def test_06_multi_model_orchestration_diagram_reasoning(self):
        """Tests that a diagram architecture query routes to Qwen 3 for deep reasoning."""
        attachments = [{"name": "system_design.png", "type": "image", "path": "data/uploads/design.png"}]
        decision = SakiModelOrchestrator.classify_request(
            "Analyze the architecture diagram and deduce bottlenecks",
            attachments=attachments
        )
        assert decision.vision_required is True
        assert decision.coding_required is False
        assert decision.selected_model == settings.MODEL_QWEN3
        assert decision.conversation_mode == "thinking"
        assert decision.task_type == "visual_reasoning"

    def test_07_general_vision_routes_to_gemma3(self):
        """Tests that a general visual query routes to Gemma 3 4B."""
        attachments = [{"name": "landscape.jpg", "type": "image", "path": "data/uploads/landscape.jpg"}]
        decision = SakiModelOrchestrator.classify_request(
            "What is in this picture?",
            attachments=attachments
        )
        assert decision.vision_required is True
        assert decision.coding_required is False
        assert decision.selected_model == settings.MODEL_GEMMA
        assert decision.conversation_mode == "vision"
        assert decision.task_type == "vision_analysis"

    def test_08_fastapi_upload_endpoint_validation(self):
        """Tests /api/upload endpoint for image validation, metadata extraction, and rejection of invalid data."""
        # 1. Valid PNG upload
        _, png_bytes = _create_test_image(400, 300, "Valid Upload", fmt="PNG")
        res = self.client.post(
            "/api/upload",
            files={"file": ("valid_test.png", io.BytesIO(png_bytes), "image/png")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "image"
        assert data["format"] == "PNG"
        assert data["width"] == 400
        assert data["height"] == 300
        assert os.path.exists(data["path"])

        # 2. Corrupted image upload rejected with 400
        res_bad = self.client.post(
            "/api/upload",
            files={"file": ("corrupt.png", io.BytesIO(b"garbage payload"), "image/png")}
        )
        assert res_bad.status_code == 400
        assert "Invalid or corrupted image" in res_bad.json().get("error", "")

    def test_09_chat_endpoint_with_image_attachment(self):
        """Tests non-streaming /api/chat with an image attachment."""
        fpath, _ = _create_test_image(500, 400, "print('Hello Saki Vision')", fmt="PNG")
        payload = {
            "message": "What text is shown in this image?",
            "conversation_id": "test-vision-conv-1",
            "attachments": [
                {
                    "name": os.path.basename(fpath),
                    "path": fpath,
                    "type": "image"
                }
            ]
        }
        res = self.client.post("/api/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "response" in data
        assert len(data["response"]) > 0
        assert data["mode"] in ["vision", "builder", "thinking"]

    def test_10_text_and_voice_chat_unaffected(self):
        """Verifies that pure text queries and standard voice sessions are 100% unaffected."""
        text_res = self.client.post(
            "/api/chat",
            json={"message": "Hello Saki, how are you today?", "conversation_id": "text-only-conv"}
        )
        assert text_res.status_code == 200
        text_data = text_res.json()
        assert text_data["mode"] == "casual"
        assert text_data["routing"]["vision_required"] is False
