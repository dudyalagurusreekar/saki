"""
Saki Event & State Definitions
Authoritative central state definitions and event structures representing real backend brain activities.
"""

import time
import uuid
import json
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SakiState(str, Enum):
    """
    Authoritative lifecycle states of Saki AI Brain.
    Driven exclusively by backend execution events.
    """
    IDLE = "IDLE"                               # Waiting for user input or passive background mode
    RECEIVED = "RECEIVED"                       # Input accepted at normalization boundary
    UNDERSTANDING = "UNDERSTANDING"             # Parsing input, detecting intent, classifying language
    RETRIEVING_CONTEXT = "RETRIEVING_CONTEXT"   # Accessing long-term memory, personal context, or RAG
    ROUTING = "ROUTING"                         # Emotion/support analysis, model orchestrator selecting specialist
    GENERATING = "GENERATING"                   # Local model inference / reasoning actively underway
    QUALITY_CHECK = "QUALITY_CHECK"             # Response evaluation, leak check, grounding check, repair
    RESPONSE_READY = "RESPONSE_READY"           # Response prepared and admitted to memory / conversation
    SPEAKING = "SPEAKING"                       # Actively streaming response text or synthesizing TTS audio
    COMPLETED = "COMPLETED"                     # Turn finished successfully
    ERROR = "ERROR"                             # System error or fail-closed boundary triggered

    # Legacy & capability-specific aliases
    LISTENING = "LISTENING"                     # Capturing / transcribing voice input (STT)
    PROCESSING = "PROCESSING"                   # Alias for UNDERSTANDING
    THINKING = "THINKING"                       # Alias for GENERATING
    SEARCHING = "SEARCHING"                     # Live web intelligence / external retrieval executing
    VISION = "VISION"                           # Multimodal image analysis / feature extraction underway
    REMEMBERING = "REMEMBERING"                 # Alias for RETRIEVING_CONTEXT
    ACTING = "ACTING"                           # Executing computer, code, or workspace capabilities


class SakiEventType(str, Enum):
    """Event classification types."""
    STATE_CHANGE = "state_change"   # Transition between SakiStates
    TOKEN = "token"                 # Single streaming token chunk
    STATUS = "status"               # Non-transitioning telemetry or activity update
    ERROR = "error"                 # Exception / error event
    LIFECYCLE = "lifecycle"         # Request start / completion boundary
    INTERRUPTION = "interruption"   # Voice barge-in / speech interruption event


class SakiEvent(BaseModel):
    """
    Standardized Saki Event Model.
    Carries complete, structured runtime information from the backend brain to the UI / consumers.
    """
    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}",
        description="Unique event ID"
    )
    event_type: SakiEventType = Field(
        default=SakiEventType.STATE_CHANGE,
        description="Type of event: state_change, token, status, error, lifecycle"
    )
    conversation_id: str = Field(
        default="default-session",
        description="Active conversation session ID"
    )
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}",
        description="Active request turn ID"
    )
    state: SakiState = Field(
        default=SakiState.IDLE,
        description="Current Saki state"
    )
    previous_state: Optional[SakiState] = Field(
        default=None,
        description="Previous Saki state before transition"
    )
    activity: Optional[str] = Field(
        default=None,
        description="Human-readable activity summary (e.g., 'Searching web for documentation')"
    )
    task: Optional[str] = Field(
        default="casual_chat",
        description="Conversational or execution task (e.g., 'casual_chat', 'concept_learning', 'bug_fixing')"
    )
    selected_model: Optional[str] = Field(
        default=None,
        description="Currently assigned Ollama model name (e.g., 'phi3:latest', 'qwen3:8b')"
    )
    detected_language: Optional[str] = Field(
        default="en",
        description="Detected ISO language code of user input (e.g., 'en', 'es', 'te')"
    )
    memory_usage: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Memory retrieval metrics (e.g., total items, retrieved context items)"
    )
    retrieval_status: Optional[str] = Field(
        default="IDLE",
        description="Status of knowledge retrieval: IDLE, RECALLING, SUFFICIENT, INSUFFICIENT, SKIPPED"
    )
    active_tool: Optional[str] = Field(
        default=None,
        description="Active capability/provider (e.g., 'GEMINI_SEARCH', 'DUCKDUCKGO', 'PIPER_TTS')"
    )
    capability: Optional[str] = Field(
        default=None,
        description="Subsystem capability name (e.g., 'WORLD_ACCESS', 'DEVELOPMENT', 'PERSONAL_CONTEXT')"
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp with sub-second precision"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Elapsed latency in milliseconds since request inception"
    )
    first_token_latency_ms: Optional[float] = Field(
        default=None,
        description="Latency in milliseconds until the first token was generated"
    )
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata specific to the event"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error description if state is ERROR"
    )

    def to_sse(self) -> str:
        """Serializes event to standard Server-Sent Events (SSE) data format."""
        data_json = self.model_dump_json()
        return f"event: {self.event_type.value}\ndata: {data_json}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        """Returns clean dictionary representation."""
        return self.model_dump()
