"""
Saki Vision Subsystem & Image Understanding Service
Processes images locally using the installed Gemma 3 4B vision model (gemma3:4b).
Provides secure image validation, smart antialiased preprocessing, structured visual
feature extraction (OCR, UI components, code, error tracebacks), and seamless handoff
to downstream specialist models (Qwen 2.5 Coder, Qwen 3).
"""

import os
import io
import time
import base64
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from PIL import Image, UnidentifiedImageError

from backend.core.config import settings
from backend.services.model_manager import model_manager, STATE_LOADING, STATE_ACTIVE, STATE_IDLE, STATE_ERROR
import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_DIMENSION = 1536  # Downscale if max(width, height) > 1536 for optimal local latency & RAM
SUPPORTED_FORMATS = {"PNG", "JPEG", "JPG", "WEBP", "GIF", "BMP"}
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


@dataclass
class ImageMetadata:
    """Metadata for an uploaded/processed image."""
    filename: str
    format: str
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    file_size_bytes: int
    was_resized: bool


@dataclass
class VisionAnalysisResult:
    """Structured visual analysis result extracted by Gemma 3 4B."""
    description: str = ""
    detected_text: str = ""
    ui_elements: List[str] = field(default_factory=list)
    errors_detected: List[str] = field(default_factory=list)
    confidence: float = 0.95
    model: str = settings.MODEL_GEMMA
    latency_ms: float = 0.0
    image_metadata: Optional[ImageMetadata] = None
    raw_response: str = ""
    success: bool = True
    error_message: Optional[str] = None

    def to_context_string(self) -> str:
        """Formats the visual extraction into structured context for orchestrator/specialist models."""
        parts = ["[Visual Inspection Context (Gemma 3 4B)]"]
        if self.description:
            parts.append(f"• Visual Description: {self.description}")
        if self.detected_text:
            parts.append(f"• Visible Text / OCR:\n```\n{self.detected_text}\n```")
        if self.ui_elements:
            parts.append(f"• Detected UI Components: {', '.join(self.ui_elements)}")
        if self.errors_detected:
            parts.append(f"• Visible Errors/Tracebacks: {', '.join(self.errors_detected)}")
        if self.image_metadata:
            parts.append(
                f"• Image Specs: {self.image_metadata.format} "
                f"{self.image_metadata.processed_width}x{self.image_metadata.processed_height} "
                f"({round(self.image_metadata.file_size_bytes / 1024, 1)} KB)"
            )
        return "\n".join(parts)


class VisionService:
    """
    Saki Vision Service coordinating local image understanding with Gemma 3 4B.
    """

    def __init__(self):
        self.model_name = settings.MODEL_GEMMA
        self._temp_files: List[str] = []

    def validate_image_file(self, file_path: str) -> Tuple[bool, Optional[str], Optional[ImageMetadata]]:
        """
        Validates an image file on disk: existence, size limit, format, and header integrity.
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}", None

        file_size = os.path.getsize(file_path)
        if file_size > MAX_IMAGE_SIZE_BYTES:
            return False, f"Image size ({round(file_size / (1024 * 1024), 2)}MB) exceeds maximum limit of 15MB", None

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return False, f"Unsupported image extension '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}", None

        try:
            with Image.open(file_path) as img:
                img.verify()  # Verify header integrity
            
            # Reopen to read dimensions since verify() closes/invalidates the image object
            with Image.open(file_path) as img:
                fmt = (img.format or ext.replace(".", "")).upper()
                w, h = img.size
                meta = ImageMetadata(
                    filename=os.path.basename(file_path),
                    format=fmt,
                    original_width=w,
                    original_height=h,
                    processed_width=w,
                    processed_height=h,
                    file_size_bytes=file_size,
                    was_resized=False
                )
                return True, None, meta
        except (UnidentifiedImageError, IOError, SyntaxError) as e:
            return False, f"Corrupted or invalid image file: {str(e)}", None
        except Exception as e:
            return False, f"Error inspecting image file: {str(e)}", None

    def validate_image_bytes(self, image_bytes: bytes, filename: str = "upload.png") -> Tuple[bool, Optional[str], Optional[ImageMetadata]]:
        """
        Validates raw image bytes in memory.
        """
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            return False, f"Image size ({round(len(image_bytes) / (1024 * 1024), 2)}MB) exceeds maximum limit of 15MB", None

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
            
            with Image.open(io.BytesIO(image_bytes)) as img:
                fmt = (img.format or "PNG").upper()
                w, h = img.size
                meta = ImageMetadata(
                    filename=filename,
                    format=fmt,
                    original_width=w,
                    original_height=h,
                    processed_width=w,
                    processed_height=h,
                    file_size_bytes=len(image_bytes),
                    was_resized=False
                )
                return True, None, meta
        except Exception as e:
            return False, f"Corrupted or invalid image data: {str(e)}", None

    def preprocess_image(self, file_path: str) -> Tuple[str, ImageMetadata]:
        """
        Loads the image, applies high-quality Lanczos downscaling if dimensions exceed MAX_DIMENSION,
        and returns a base64 encoded string along with updated ImageMetadata.
        """
        with Image.open(file_path) as img:
            fmt = img.format or "PNG"
            # Convert RGBA/P to RGB if saving as JPEG
            orig_w, orig_h = img.size
            new_w, new_h = orig_w, orig_h
            was_resized = False

            if max(orig_w, orig_h) > MAX_DIMENSION:
                scale = MAX_DIMENSION / float(max(orig_w, orig_h))
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                was_resized = True

            buffered = io.BytesIO()
            # Preserve PNG or JPEG
            save_fmt = "PNG" if fmt.upper() in ["PNG", "WEBP", "GIF"] else "JPEG"
            if save_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buffered, format=save_fmt, quality=92, optimize=True)
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")

            meta = ImageMetadata(
                filename=os.path.basename(file_path),
                format=fmt.upper(),
                original_width=orig_w,
                original_height=orig_h,
                processed_width=new_w,
                processed_height=new_h,
                file_size_bytes=len(buffered.getvalue()),
                was_resized=was_resized
            )
            return encoded, meta

    def is_gemma_available(self) -> bool:
        """Checks if Gemma 3 4B is available in the local Ollama instance."""
        try:
            res = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
            if res.status_code == 200:
                models = [m.get("name", "") for m in res.json().get("models", [])]
                return any(self.model_name in m or m.startswith("gemma3") for m in models)
        except Exception:
            pass
        return False

    def build_vision_prompt(self, user_query: str, task_type: str = "general") -> str:
        """
        Constructs an optimized visual feature extraction prompt for Gemma 3 4B.
        """
        if task_type in ["visual_coding_task", "code_screenshot"]:
            return (
                f"You are Saki's visual perception engine. Analyze this screenshot in detail.\n"
                f"User Question: {user_query}\n\n"
                f"Provide a structured extraction:\n"
                f"1. VISUAL DESCRIPTION: Overview of what is visible (IDE, browser, terminal, app).\n"
                f"2. CODE & OCR: Transcribe the exact visible code, terminal text, or syntax verbatim without alterations.\n"
                f"3. UI ELEMENTS: Note relevant UI buttons, line numbers, tabs, or panels.\n"
                f"4. ERRORS & TRACEBACKS: Explicitly extract any visible error messages, red underlines, or exception logs.\n"
                f"5. OBSERVATION NOTES: Highlight key visual cues (highlighted lines, cursor position, active file)."
            )
        elif task_type in ["visual_reasoning", "diagram_analysis"]:
            return (
                f"You are Saki's visual perception engine. Analyze this diagram, chart, or visual document.\n"
                f"User Question: {user_query}\n\n"
                f"Provide a structured breakdown:\n"
                f"1. VISUAL DESCRIPTION: Complete summary of the diagram structure, nodes, flowchart, or chart type.\n"
                f"2. VISIBLE TEXT & LABELS: All text labels, axis titles, legends, node labels, and numbers.\n"
                f"3. RELATIONSHIPS & FLOW: Connections, arrows, hierarchies, sequence of steps, or mathematical formulas.\n"
                f"4. KEY OBSERVATIONS: Notable data points, trends, or logical relationships."
            )
        else:
            return (
                f"You are Saki's visual perception engine. Analyze this image carefully.\n"
                f"User Question: {user_query}\n\n"
                f"Describe the image thoroughly:\n"
                f"1. What is in the image (objects, people, scene, environment, colors)?\n"
                f"2. Any visible text or signage.\n"
                f"3. Key details and spatial layout relevant to the user's question: {user_query}"
            )

    def parse_structured_vision_response(self, raw_text: str, meta: Optional[ImageMetadata] = None, latency_ms: float = 0.0) -> VisionAnalysisResult:
        """
        Parses Gemma's visual response into a structured VisionAnalysisResult.
        """
        res = VisionAnalysisResult(
            raw_response=raw_text,
            description=raw_text.strip(),
            confidence=0.95,
            model=self.model_name,
            latency_ms=latency_ms,
            image_metadata=meta,
            success=True
        )

        # Extract OCR/Code blocks
        code_blocks = re.findall(r"```(?:[a-zA-Z0-9_-]*\n)?(.*?)```", raw_text, re.DOTALL)
        if code_blocks:
            res.detected_text = "\n\n".join(cb.strip() for cb in code_blocks)

        # Look for structured sections if provided by the model
        ocr_match = re.search(r"(?:CODE & OCR|VISIBLE TEXT|OCR):\s*(.*?)(?=\n[0-9]\.|\n[A-Z &]+:|$)", raw_text, re.DOTALL | re.IGNORECASE)
        if ocr_match and not res.detected_text:
            res.detected_text = ocr_match.group(1).strip()

        desc_match = re.search(r"(?:VISUAL DESCRIPTION|DESCRIPTION|OVERVIEW):\s*(.*?)(?=\n[0-9]\.|\n[A-Z &]+:|$)", raw_text, re.DOTALL | re.IGNORECASE)
        if desc_match:
            res.description = desc_match.group(1).strip()

        err_match = re.search(r"(?:ERRORS & TRACEBACKS|ERRORS|TRACEBACK):\s*(.*?)(?=\n[0-9]\.|\n[A-Z &]+:|$)", raw_text, re.DOTALL | re.IGNORECASE)
        if err_match:
            err_text = err_match.group(1).strip()
            if err_text.lower() not in ["none", "n/a", "no errors visible", "none visible"]:
                res.errors_detected = [e.strip("- *") for e in err_text.split("\n") if e.strip("- *")]

        ui_match = re.search(r"(?:UI ELEMENTS|UI COMPONENTS|LAYOUT):\s*(.*?)(?=\n[0-9]\.|\n[A-Z &]+:|$)", raw_text, re.DOTALL | re.IGNORECASE)
        if ui_match:
            ui_text = ui_match.group(1).strip()
            if ui_text.lower() not in ["none", "n/a"]:
                res.ui_elements = [u.strip("- *") for u in ui_text.split("\n") if u.strip("- *")]

        return res

    def analyze_image(
        self,
        image_path: str,
        user_query: str = "Describe this image",
        task_type: str = "general"
    ) -> VisionAnalysisResult:
        """
        Executes local vision inspection with Gemma 3 4B on the given image.
        """
        # 1. Validate image
        valid, err, meta = self.validate_image_file(image_path)
        if not valid:
            return VisionAnalysisResult(
                success=False,
                error_message=err,
                confidence=0.0,
                model=self.model_name
            )

        # 2. Preprocess & encode
        try:
            b64_img, updated_meta = self.preprocess_image(image_path)
        except Exception as e:
            return VisionAnalysisResult(
                success=False,
                error_message=f"Preprocessing failed: {str(e)}",
                confidence=0.0,
                model=self.model_name
            )

        # 3. Formulate prompt
        prompt = self.build_vision_prompt(user_query, task_type=task_type)

        # 4. Call Ollama Gemma 3 4B
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "images": [b64_img],
            "keep_alive": settings.MODEL_KEEP_ALIVE_SESSION
        }

        from backend.services.resource_manager import resource_manager, ResourceState

        with resource_manager.acquire("vision_pipeline"):
            with resource_manager.acquire(self.model_name):
                start_t = time.time()
                try:
                    res = httpx.post(
                        f"{OLLAMA_BASE_URL}/api/generate",
                        json=payload,
                        timeout=60.0
                    )
                    latency_ms = (time.time() - start_t) * 1000

                    if res.status_code == 200:
                        data = res.json()
                        raw_text = data.get("response", "").strip()
                        
                        # Record telemetry
                        model_manager.record_telemetry(
                            model=self.model_name,
                            mode="vision",
                            latency_ms=latency_ms,
                            first_token_latency=latency_ms * 0.35,
                            tokens_per_second=data.get("eval_count", 30) / max(0.001, latency_ms / 1000.0),
                            input_tokens=data.get("prompt_eval_count", len(prompt.split())),
                            output_tokens=data.get("eval_count", len(raw_text.split()))
                        )

                        return self.parse_structured_vision_response(raw_text, updated_meta, latency_ms)
                    else:
                        resource_manager.set_component_state(self.model_name, ResourceState.ERROR, f"HTTP {res.status_code}")
                        return VisionAnalysisResult(
                            success=False,
                            error_message=f"Local vision model returned HTTP {res.status_code}: {res.text}",
                            confidence=0.0,
                            model=self.model_name,
                            latency_ms=latency_ms,
                            image_metadata=updated_meta
                        )
                except httpx.ConnectError:
                    resource_manager.set_component_state(self.model_name, ResourceState.ERROR, "ConnectError")
                    return VisionAnalysisResult(
                        success=False,
                        error_message="Cannot connect to Ollama. Ensure Ollama service is active.",
                        confidence=0.0,
                        model=self.model_name,
                        image_metadata=updated_meta
                    )
                except Exception as e:
                    resource_manager.set_component_state(self.model_name, ResourceState.ERROR, str(e))
                    return VisionAnalysisResult(
                        success=False,
                        error_message=f"Vision model execution failed: {str(e)}",
                        confidence=0.0,
                        model=self.model_name,
                        image_metadata=updated_meta
                    )

    def cleanup_temporary_files(self) -> int:
        """Removes any registered temporary image files."""
        cleaned = 0
        for p in self._temp_files:
            if os.path.exists(p):
                try:
                    os.remove(p)
                    cleaned += 1
                except Exception:
                    pass
        self._temp_files.clear()
        return cleaned


# Global vision service singleton
vision_service = VisionService()
