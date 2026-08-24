from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class InputType(str, Enum):
    TEXT = "TEXT"
    VOICE = "VOICE"
    IMAGE = "IMAGE"
    MULTIMODAL = "MULTIMODAL"

class RequestInput(BaseModel):
    message: str = ""
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_id: str = "default-session"
    turn_id: Optional[str] = None
    input_type: InputType = InputType.TEXT
    language_hint: Optional[str] = None
    language_mode: Optional[str] = "AUTO"
    voice_metadata: Optional[Dict[str, Any]] = None
    current_context: Optional[Dict[str, Any]] = None
    enable_tts: bool = False
    voice: Optional[str] = None
    speed: Optional[float] = None
    is_voice_mode: bool = False

class UnifiedTurnRequest(BaseModel):
    """
    Standard normalized request schema for the Unified Saki Brain.
    Unifies Text, Voice, Image, and Multimodal turns into one pipeline.
    """
    input_type: InputType = Field(default=InputType.TEXT, description="Input modality: TEXT, VOICE, IMAGE, MULTIMODAL")
    text: str = Field(default="", description="Clean text or transcribed speech transcript")
    conversation_id: str = Field(default="default-session", description="Active conversation session ID")
    turn_id: str = Field(default_factory=lambda: f"turn_{int(__import__('time').time() * 1000)}", description="Unique turn ID")
    language_hint: Optional[str] = Field(default=None, description="Optional caller language hint")
    language_mode: Optional[str] = Field(default="AUTO", description="Caller language mode: AUTO, EN, TE, KN")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Parsed attachment metadata or file paths")
    voice_metadata: Optional[Dict[str, Any]] = Field(default=None, description="STT telemetry, audio metrics, play_locally flag")
    current_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Active project, workspace, temporal state")
    enable_tts: bool = Field(default=False, description="Whether to synthesize speech for the response")
    voice: Optional[str] = Field(default=None, description="Selected voice identifier (e.g. af_heart, te_saki)")
    speed: Optional[float] = Field(default=1.0, description="Speech rate multiplier")
    is_voice_mode: bool = Field(default=False, description="Whether turn is part of a voice session")

class NormalizedRequest(BaseModel):
    id: str = Field(description="UUID request / turn ID")
    turn_id: Optional[str] = Field(default=None, description="Explicit turn ID")
    input_type: InputType = Field(default=InputType.TEXT, description="Input modality: TEXT, VOICE, IMAGE, MULTIMODAL")
    query: str = Field(description="Clean, normalized query text")
    language: str = Field(default="en", description="Detected language code")
    language_mode: str = Field(default="AUTO", description="Language mode: AUTO, EN, TE, KN")
    urls: List[str] = Field(default_factory=list, description="Extracted unique URLs")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Analyzed attachments metadata")
    voice_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Voice telemetry and audio metadata")
    current_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Active project and contextual state")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")
    is_markdown: bool = Field(default=False, description="True if input has markdown structure")

class LanguageResult(BaseModel):
    language: str
    confidence: float

class AttachmentMetadata(BaseModel):
    name: str
    type: str = Field(description="File extension or classified type (pdf, docx, txt, csv, image, zip, etc.)")
    pages: Optional[int] = Field(default=None, description="Number of pages or files or rows depending on type")
    size: str = Field(description="Formatted human-readable size, e.g., 8MB, 450KB")
    checksum: str = Field(description="SHA-256 checksum of the file")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra parsed metadata")

class URLClassification(BaseModel):
    url: str
    domain: str
    category: str = Field(description="github, youtube, docs, wikipedia, pdf, blog")

class IntentResult(BaseModel):
    intent: str = Field(description="Predicted intent category")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")

class EntityResult(BaseModel):
    entities: List[str] = Field(default_factory=list, description="List of simple entity text strings")
    structured_entities: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Structured entities with text and type (e.g., {'text': 'FastAPI', 'type': 'Framework'})"
    )

class ComplexityResult(BaseModel):
    complexity: str = Field(description="Simple, Medium, Complex, Research, Long Running")
    estimated_steps: int = Field(description="Estimated execution steps")

class TaskPlan(BaseModel):
    steps: List[str] = Field(default_factory=list, description="Executable list of step names")

class RouteResult(BaseModel):
    route: List[str] = Field(default_factory=list, description="Selected information sources")

class ContextItem(BaseModel):
    source: str = Field(description="Source of the context item, e.g., memory, browser, etc.")
    score: float = Field(description="Relevance score")
    content: str = Field(description="Context content text")
    citation: Optional[str] = Field(default=None, description="Source citation reference link or ID")

class ContextResult(BaseModel):
    context: List[ContextItem] = Field(default_factory=list, description="Ranked and compressed context items")
