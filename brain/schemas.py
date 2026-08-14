from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class RequestInput(BaseModel):
    message: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)

class NormalizedRequest(BaseModel):
    id: str = Field(description="UUID request ID")
    query: str = Field(description="Clean, normalized query text")
    language: str = Field(default="en", description="Detected language code")
    urls: List[str] = Field(default_factory=list, description="Extracted unique URLs")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Analyzed attachments metadata")
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
