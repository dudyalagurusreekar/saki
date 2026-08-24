"""
Saki Event System & Central State Manager
Manages real-time SakiState transitions, event logging, and pub/sub distribution across the backend and frontend.
"""

import time
import queue
import asyncio
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Callable, Generator, AsyncGenerator
from backend.core.events import SakiState, SakiEventType, SakiEvent


class SakiEventManager:
    """
    Thread-safe and Async-compatible Event Manager for Saki.
    Maintains session state registry, timing metrics, and broadcasts state changes to active listeners.
    """
    _instance: Optional["SakiEventManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SakiEventManager, cls).__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self._current_states: Dict[str, SakiState] = {}          # conv_id -> SakiState
        self._request_start_times: Dict[str, float] = {}        # req_id -> start_timestamp
        self._request_first_tokens: Dict[str, float] = {}       # req_id -> first_token_timestamp
        self._sync_subscribers: Dict[str, List[queue.Queue]] = {} # conv_id -> list of Queue
        self._async_subscribers: Dict[str, List[asyncio.Queue]] = {} # conv_id -> list of AsyncQueue
        self._global_sync_subscribers: List[queue.Queue] = []
        self._global_async_subscribers: List[asyncio.Queue] = []
        self._event_history: Dict[str, List[SakiEvent]] = {}    # conv_id -> list of SakiEvent (last 50)
        self._state_lock = threading.RLock()

    def get_current_state(self, conversation_id: str = "default-session") -> SakiState:
        """Returns the current state for a conversation, defaulting to IDLE."""
        with self._state_lock:
            return self._current_states.get(conversation_id, SakiState.IDLE)

    def start_request(self, conversation_id: str, request_id: str):
        """Records the inception time for a request turn."""
        with self._state_lock:
            self._request_start_times[request_id] = time.time()
            if conversation_id not in self._event_history:
                self._event_history[conversation_id] = []

    def record_first_token(self, request_id: str) -> Optional[float]:
        """Records timestamp of the first token and returns latency in ms."""
        with self._state_lock:
            start_time = self._request_start_times.get(request_id)
            if start_time and request_id not in self._request_first_tokens:
                now = time.time()
                self._request_first_tokens[request_id] = now
                return round((now - start_time) * 1000, 2)
            elif start_time and request_id in self._request_first_tokens:
                return round((self._request_first_tokens[request_id] - start_time) * 1000, 2)
            return None

    def emit(self, event: SakiEvent):
        """Broadcasts an event to all subscribers of the conversation and global subscribers."""
        with self._state_lock:
            conv_id = event.conversation_id
            
            # Store in local history (capped at 50 events per conversation)
            if conv_id not in self._event_history:
                self._event_history[conv_id] = []
            self._event_history[conv_id].append(event)
            if len(self._event_history[conv_id]) > 50:
                self._event_history[conv_id] = self._event_history[conv_id][-50:]

            # Sync subscribers for session
            for q in list(self._sync_subscribers.get(conv_id, [])):
                try:
                    q.put_nowait(event)
                except Exception:
                    pass

            # Global sync subscribers
            for q in list(self._global_sync_subscribers):
                try:
                    q.put_nowait(event)
                except Exception:
                    pass

            # Async subscribers
            for aq in list(self._async_subscribers.get(conv_id, [])):
                try:
                    aq.put_nowait(event)
                except Exception:
                    pass

            for aq in list(self._global_async_subscribers):
                try:
                    aq.put_nowait(event)
                except Exception:
                    pass

    def transition(
        self,
        conversation_id: str,
        request_id: str,
        new_state: SakiState,
        activity: Optional[str] = None,
        task: Optional[str] = None,
        selected_model: Optional[str] = None,
        detected_language: Optional[str] = "en",
        memory_usage: Optional[Dict[str, Any]] = None,
        retrieval_status: Optional[str] = None,
        active_tool: Optional[str] = None,
        capability: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        event_type: SakiEventType = SakiEventType.STATE_CHANGE
    ) -> SakiEvent:
        """
        Executes a formal state transition.
        Calculates elapsed latency, updates internal state, and emits SakiEvent.
        """
        with self._state_lock:
            prev_state = self._current_states.get(conversation_id, SakiState.IDLE)
            self._current_states[conversation_id] = new_state

            # Compute elapsed request latency if tracking
            start_time = self._request_start_times.get(request_id)
            latency_ms = round((time.time() - start_time) * 1000, 2) if start_time else None
            first_token_ms = None
            if request_id in self._request_first_tokens and start_time:
                first_token_ms = round((self._request_first_tokens[request_id] - start_time) * 1000, 2)

            event = SakiEvent(
                event_type=event_type,
                conversation_id=conversation_id,
                request_id=request_id,
                state=new_state,
                previous_state=prev_state,
                activity=activity,
                task=task or "casual_chat",
                selected_model=selected_model,
                detected_language=detected_language or "en",
                memory_usage=memory_usage or {},
                retrieval_status=retrieval_status or "IDLE",
                active_tool=active_tool,
                capability=capability,
                timestamp=time.time(),
                latency_ms=latency_ms,
                first_token_latency_ms=first_token_ms,
                details=details or {},
                error=error
            )

            # Cleanup timer on IDLE or ERROR completion
            if new_state in [SakiState.IDLE, SakiState.ERROR] and event_type == SakiEventType.STATE_CHANGE:
                self._request_start_times.pop(request_id, None)
                self._request_first_tokens.pop(request_id, None)

            self.emit(event)
            return event

    def subscribe_sync(self, conversation_id: Optional[str] = None) -> queue.Queue:
        """Subscribes a synchronous queue to events for a specific conversation or globally."""
        with self._state_lock:
            q = queue.Queue(maxsize=100)
            if conversation_id:
                if conversation_id not in self._sync_subscribers:
                    self._sync_subscribers[conversation_id] = []
                self._sync_subscribers[conversation_id].append(q)
            else:
                self._global_sync_subscribers.append(q)
            return q

    def unsubscribe_sync(self, q: queue.Queue, conversation_id: Optional[str] = None):
        """Removes a synchronous queue subscriber."""
        with self._state_lock:
            if conversation_id and conversation_id in self._sync_subscribers:
                if q in self._sync_subscribers[conversation_id]:
                    self._sync_subscribers[conversation_id].remove(q)
            if q in self._global_sync_subscribers:
                self._global_sync_subscribers.remove(q)

    def subscribe_async(self, conversation_id: Optional[str] = None) -> asyncio.Queue:
        """Subscribes an asyncio queue to events for a specific conversation or globally."""
        with self._state_lock:
            aq = asyncio.Queue(maxsize=100)
            if conversation_id:
                if conversation_id not in self._async_subscribers:
                    self._async_subscribers[conversation_id] = []
                self._async_subscribers[conversation_id].append(aq)
            else:
                self._global_async_subscribers.append(aq)
            return aq

    def unsubscribe_async(self, aq: asyncio.Queue, conversation_id: Optional[str] = None):
        """Removes an asyncio queue subscriber."""
        with self._state_lock:
            if conversation_id and conversation_id in self._async_subscribers:
                if aq in self._async_subscribers[conversation_id]:
                    self._async_subscribers[conversation_id].remove(aq)
            if aq in self._global_async_subscribers:
                self._global_async_subscribers.remove(aq)

    def get_event_history(self, conversation_id: str = "default-session") -> List[SakiEvent]:
        """Returns the recent event history for a conversation."""
        with self._state_lock:
            return list(self._event_history.get(conversation_id, []))


# Global singleton instance
event_manager = SakiEventManager()
saki_event_manager = event_manager


@contextmanager
def saki_state_scope(
    conversation_id: str,
    request_id: str,
    initial_state: SakiState = SakiState.PROCESSING,
    activity: Optional[str] = "Processing request",
    task: Optional[str] = "casual_chat",
    selected_model: Optional[str] = None,
    detected_language: Optional[str] = "en"
):
    """
    Context manager ensuring deterministic lifecycle management.
    Enters initial_state, yields transition function, and guarantees IDLE or ERROR transition on exit.
    """
    event_manager.start_request(conversation_id, request_id)
    event_manager.transition(
        conversation_id=conversation_id,
        request_id=request_id,
        new_state=initial_state,
        activity=activity,
        task=task,
        selected_model=selected_model,
        detected_language=detected_language
    )
    try:
        yield event_manager
    except Exception as e:
        event_manager.transition(
            conversation_id=conversation_id,
            request_id=request_id,
            new_state=SakiState.ERROR,
            activity="Error encountered during execution",
            error=str(e)
        )
        raise
    finally:
        # Reset to IDLE cleanly on scope exit if not already IDLE
        if event_manager.get_current_state(conversation_id) != SakiState.IDLE:
            event_manager.transition(
                conversation_id=conversation_id,
                request_id=request_id,
                new_state=SakiState.IDLE,
                activity="Ready for next message"
            )
