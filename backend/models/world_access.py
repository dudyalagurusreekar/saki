from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorldAccessAction(str, Enum):
    SEARCH = "search"
    FETCH = "fetch"


class DataClass(str, Enum):
    PUBLIC = "public"
    CONTEXTUAL = "contextual"
    PERSONAL = "personal"
    SECRET = "secret"


class PrivacyDecision(BaseModel):
    allowed: bool
    mode: str
    data_class: DataClass = DataClass.PUBLIC
    sanitized_query: Optional[str] = None
    blocked_reasons: List[str] = Field(default_factory=list)


class WorldAccessRequest(BaseModel):
    action: WorldAccessAction
    query: Optional[str] = None
    url: Optional[str] = None
    reason: str = ""
    require_freshness: bool = False
    max_results: int = Field(default=5, ge=1, le=20)


class EvidenceItem(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""
    retrieved_at: float
    freshness: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldAccessResult(BaseModel):
    action: WorldAccessAction
    query: Optional[str] = None
    allowed: bool
    evidence: List[EvidenceItem] = Field(default_factory=list)
    privacy: PrivacyDecision
    error: Optional[str] = None
    retrieved_at: float
