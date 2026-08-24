"""
Unified Saki Brain Turn Engine (Sprint 1)
Authoritative central pipeline executing all Text, Voice, Image, and Multimodal turns.

Pipeline sequence:
TEXT / VOICE / IMAGE 
  → Input Normalizer 
  → Conversation Context 
  → Emotion/Support Analysis 
  → Language Analysis 
  → Relevant Memory 
  → Task/Capability Classification 
  → Existing Orchestrator 
  → Specialist Model 
  → Response Quality Check 
  → Unified Response 
  → Chat Display 
  → TTS when voice mode is active 
  → Core Events
"""

import os
import re
import time
import uuid
import base64
import threading
import traceback
from typing import Optional, List, Dict, Any, Union

from backend.core.config import settings
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    UnifiedTurnRequestSchema,
    ResponsePlanSchema,
    EvaluationResultSchema,
    SakiAwarenessSchema,
    EvidenceItemSchema,
    EvidencePackageSchema,
    ResearchResultSchema,
    BrowserObservationSchema,
    ComputerObservationSchema,
    DevelopmentTaskSchema,
    GitGitHubTelemetrySchema,
    SakiTaskSchema,
    PersonalContextTelemetrySchema,
    UnifiedKnowledgePackageSchema,
    KnowledgeCandidateSchema,
    FusedKnowledgePackageSchema,
    FusedClaimSchema,
    SourceConflictSchema,
    KnowledgeGraphPackageSchema,
    KnowledgeNodeSchema,
    KnowledgeEdgeSchema,
    WebIntelligenceTelemetrySchema,
    AdaptiveIntelligenceTelemetrySchema,
    WorkflowTelemetrySchema,
    SakiEventSchema
)

from brain.schemas import UnifiedTurnRequest, NormalizedRequest, InputType
from brain.request_normalizer import normalize_request
from backend.core.events import SakiState, SakiEventType, SakiEvent
from backend.services.event_system import event_manager, saki_event_manager
from backend.services.ai_service import call_model
from backend.services.orchestrator import SakiModelOrchestrator, RoutingDecision
from backend.services.emotional_intelligence import SakiAwareness
from backend.services.memory_service import build_smart_memory_context, load_memory, update_memory
from backend.services.response_planner import plan_response, ResponsePlan
from backend.services.response_evaluator import evaluate_response, clean_speaker_tags
from backend.services.learning_service import detect_user_correction
from backend.services.search_service import safe_search
from backend.services.model_manager import model_manager
from backend.services.tts_service import tts_service
from backend.services.vision_service import vision_service
from backend.services.multilingual_service import multilingual_service, LanguageProfile
from backend.services.translation_service import translation_service
from backend.core.config import settings
from backend.core.saki_persona import build_saki_system_prompt, format_prompt_for_model
from backend.routes.chat import (
    _load_conversations_data,
    _save_conversations_data,
    append_message_to_conversation,
    get_attachment_context,
    format_history_context,
    build_orchestrated_prompt
)


# -------------------------------------------------------------
# 1. TURN DEDUPLICATOR & CONCURRENCY GUARD
# -------------------------------------------------------------
class TurnDeduplicator:
    """
    Thread-safe registry tracking active and completed turn IDs.
    Prevents duplicate submissions, duplicate assistant messages,
    stale TTS callbacks, and concurrent duplicate turns.
    """
    def __init__(self, ttl_seconds: float = 300.0):
        self._lock = threading.Lock()
        self._in_flight: Dict[str, float] = {}             # turn_key -> start_time
        self._completed_cache: Dict[str, Any] = {}         # turn_key -> (timestamp, ChatResponse)
        self._ttl_seconds = ttl_seconds

    def _make_key(self, conv_id: str, turn_id: str) -> str:
        return f"{conv_id}::{turn_id}"

    def register_turn(self, conv_id: str, turn_id: str) -> bool:
        """
        Attempts to register a new turn.
        Returns True if turn is accepted (not duplicate).
        Returns False if turn is already in-flight or recently processed.
        """
        if not turn_id:
            return True
        key = self._make_key(conv_id, turn_id)
        now = time.time()
        with self._lock:
            # Purge expired cache entries
            expired = [k for k, (ts, _) in self._completed_cache.items() if now - ts > self._ttl_seconds]
            for k in expired:
                del self._completed_cache[k]

            # If already in flight, reject duplicate submission
            if key in self._in_flight:
                return False

            # If already completed recently, check cache
            if key in self._completed_cache:
                return False

            self._in_flight[key] = now
            return True

    def get_cached_response(self, conv_id: str, turn_id: str) -> Optional[ChatResponse]:
        """Returns cached ChatResponse for a previously completed turn ID."""
        if not turn_id:
            return None
        key = self._make_key(conv_id, turn_id)
        with self._lock:
            if key in self._completed_cache:
                _, resp = self._completed_cache[key]
                return resp
            return None

    def complete_turn(self, conv_id: str, turn_id: str, response: ChatResponse):
        """Marks turn as completed and caches response."""
        if not turn_id:
            return
        key = self._make_key(conv_id, turn_id)
        now = time.time()
        with self._lock:
            if key in self._in_flight:
                del self._in_flight[key]
            self._completed_cache[key] = (now, response)

    def release_turn(self, conv_id: str, turn_id: str):
        """Releases an in-flight turn lock on error."""
        if not turn_id:
            return
        key = self._make_key(conv_id, turn_id)
        with self._lock:
            if key in self._in_flight:
                del self._in_flight[key]


turn_deduplicator = TurnDeduplicator()


# -------------------------------------------------------------
# 2. UNIFIED SAKI BRAIN TURN ENGINE
# -------------------------------------------------------------
class UnifiedBrainEngine:
    """
    Unified Saki Brain Execution Pipeline.
    Guarantees all inputs (Text, Voice, Image, Multimodal) flow through
    the identical brain pipeline, sharing memory, persona, emotional state,
    orchestrator routing, and response schemas.
    """

    @staticmethod
    def execute_turn(
        req_input: Union[ChatRequest, UnifiedTurnRequest, UnifiedTurnRequestSchema, Dict[str, Any]],
        override_turn_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Executes a single unified brain turn across all stages:
        RECEIVED → UNDERSTANDING → RETRIEVING_CONTEXT → ROUTING → GENERATING → QUALITY_CHECK → RESPONSE_READY → SPEAKING → COMPLETED
        """
        t_start = time.perf_counter()

        # ---------------------------------------------------------
        # STAGE 1: INPUT NORMALIZATION & RECEIVED STATE
        # ---------------------------------------------------------
        norm_req: NormalizedRequest = normalize_request(req_input)
        
        # Extract metadata
        conv_id = (
            getattr(req_input, "conversation_id", None) 
            or (req_input.get("conversation_id") if isinstance(req_input, dict) else None)
            or "default-session"
        )
        turn_id = (
            override_turn_id 
            or getattr(req_input, "turn_id", None) 
            or (req_input.get("turn_id") if isinstance(req_input, dict) else None)
            or norm_req.turn_id 
            or f"turn_{norm_req.id[:12]}"
        )
        req_id = norm_req.id
        user_input = norm_req.query
        attachments = norm_req.attachments or []
        input_type_enum = norm_req.input_type
        input_type_str = input_type_enum.value if hasattr(input_type_enum, "value") else str(input_type_enum)
        
        enable_tts = bool(
            getattr(req_input, "enable_tts", False) 
            or (req_input.get("enable_tts") if isinstance(req_input, dict) else False)
            or getattr(req_input, "is_voice_mode", False)
            or (req_input.get("is_voice_mode") if isinstance(req_input, dict) else False)
            or input_type_str == "VOICE"
        )
        is_voice_mode = bool(
            getattr(req_input, "is_voice_mode", False)
            or (req_input.get("is_voice_mode") if isinstance(req_input, dict) else False)
            or input_type_str == "VOICE"
        )
        voice_override = (
            getattr(req_input, "voice", None) 
            or (req_input.get("voice") if isinstance(req_input, dict) else None)
        )
        speed_override = (
            getattr(req_input, "speed", None) 
            or (req_input.get("speed") if isinstance(req_input, dict) else None)
        )

        # ---------------------------------------------------------
        # STAGE 1.1: TURN DEDUPLICATION & OVERLAP CHECK
        # ---------------------------------------------------------
        cached = turn_deduplicator.get_cached_response(conv_id, turn_id)
        if cached is not None:
            return cached

        if not turn_deduplicator.register_turn(conv_id, turn_id):
            # Duplicate / concurrent submission detected
            cached_retry = turn_deduplicator.get_cached_response(conv_id, turn_id)
            if cached_retry is not None:
                return cached_retry
            return ChatResponse(
                response="I am already processing this request.",
                intent="duplicate_request_rejected",
                mode="casual",
                final_state="COMPLETED",
                turn_id=turn_id,
                request_id=req_id,
                conversation_id=conv_id,
                input_type=input_type_str
            )

        pipeline_events: List[SakiEvent] = []
        mgr = saki_event_manager or event_manager

        try:
            # Start request telemetry
            mgr.start_request(conv_id, req_id)

            # Emit State: RECEIVED
            e_recv = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.RECEIVED,
                activity=f"Input accepted via {input_type_str} modality",
                details={
                    "turn_id": turn_id,
                    "input_type": input_type_str,
                    "has_attachments": bool(attachments),
                    "is_voice_mode": is_voice_mode
                }
            )
            pipeline_events.append(e_recv)

            # ---------------------------------------------------------
            # STAGE 2: UNDERSTANDING & LANGUAGE ANALYSIS
            # ---------------------------------------------------------
            lang_mode = getattr(req_input, "language_mode", None) or (req_input.get("language_mode") if isinstance(req_input, dict) else None) or norm_req.language_mode or "AUTO"
            temp_memory = load_memory()
            recent_turns = temp_memory.get("conversation_history", [])
            lang_profile = multilingual_service.classify_text(user_input, recent_history=recent_turns) if user_input else LanguageProfile(language=norm_req.language)
            
            target_lang_profile = multilingual_service.determine_target_response_language(
                input_profile=lang_profile,
                user_query=user_input,
                manual_mode=lang_mode,
                recent_history=recent_turns
            )
            det_lang = target_lang_profile.language or lang_profile.language or "en"

            e_und = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.UNDERSTANDING,
                activity="Analyzing language, semantic intent, and structure",
                detected_language=det_lang,
                details={
                    "language": det_lang,
                    "primary_language": target_lang_profile.primary_language,
                    "secondary_language": target_lang_profile.secondary_language,
                    "input_language": lang_profile.language,
                    "target_language": target_lang_profile.language,
                    "language_mode": lang_mode,
                    "is_code_mixed": target_lang_profile.is_code_mixed,
                    "confidence": target_lang_profile.confidence,
                    "detection_source": target_lang_profile.detection_source,
                    "language_segments": target_lang_profile.language_segments,
                    "is_markdown": norm_req.is_markdown,
                    "extracted_urls": norm_req.urls
                }
            )
            pipeline_events.append(e_und)

            # ---------------------------------------------------------
            # STAGE 2.5: INPUT TRANSLATION (user language → English)
            # All downstream routing, memory retrieval, and generation
            # operate on stable English text exactly like normal chat.
            # ---------------------------------------------------------
            english_input = user_input
            input_translated = False
            if (
                user_input
                and getattr(settings, "ENABLE_TRANSLATION", True)
                and translation_service.needs_translation(lang_profile.language)
            ):
                e_tr_in = mgr.transition(
                    conversation_id=conv_id,
                    request_id=req_id,
                    new_state=SakiState.UNDERSTANDING,
                    activity=f"Translating input from {target_lang_profile.language_label} to English",
                    detected_language=det_lang,
                    details={"translation_direction": "input_to_english"}
                )
                pipeline_events.append(e_tr_in)

                english_input = translation_service.to_english(
                    user_input,
                    source_lang=lang_profile.language
                )
                input_translated = english_input != user_input

            # ---------------------------------------------------------
            # STAGE 3: RELEVANT MEMORY & CONVERSATION CONTEXT
            # ---------------------------------------------------------
            memory = load_memory()
            
            # Check for user correction (Learning Loop) — English-normalized text
            if english_input:
                correction = detect_user_correction(english_input)
                if correction:
                    from backend.services.memory_service import _upsert_memory
                    _upsert_memory(memory, correction)

            prev_awareness_raw = memory.get("awareness")
            prev_awareness = SakiAwareness(**prev_awareness_raw) if prev_awareness_raw else None
            active_proj = prev_awareness.current_project if prev_awareness else "Saki"

            e_ctx = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.RETRIEVING_CONTEXT,
                activity=f"Recalling memory and personal context for project '{active_proj}'",
                detected_language=det_lang,
                retrieval_status="RECALLING",
                memory_usage={
                    "history_turns": len(memory.get("conversation_history", [])),
                    "durable_memories": len(memory.get("memories", []))
                }
            )
            pipeline_events.append(e_ctx)

            # ---------------------------------------------------------
            # STAGE 4: TASK CLASSIFICATION & EXISTING ORCHESTRATOR ROUTING
            # ---------------------------------------------------------
            recent_turns = memory.get("conversation_history", [])
            decision: RoutingDecision = SakiModelOrchestrator.classify_request(
                query=english_input,
                attachments=attachments,
                previous_awareness=prev_awareness,
                memory_data=memory,
                is_voice_mode=is_voice_mode,
                recent_history=recent_turns
            )
            action = decision.action_decision
            selected_model = decision.selected_model
            current_task = decision.cognitive_state.conversation.task

            e_rout = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.ROUTING,
                activity=f"Routing turn to specialist model '{selected_model}' ({decision.conversation_mode} mode)",
                task=current_task,
                selected_model=selected_model,
                detected_language=det_lang,
                details={
                    "conversation_mode": decision.conversation_mode,
                    "task_type": decision.task_type,
                    "action": action.action if action else "NONE",
                    "requires_world_access": action.requires_world_access if action else False
                }
            )
            pipeline_events.append(e_rout)

            # ---------------------------------------------------------
            # STAGE 4.5: GATED SUBSYSTEMS (VISION, WORLD ACCESS, DEV)
            # ---------------------------------------------------------
            image_paths = []
            if attachments:
                for att in attachments:
                    if isinstance(att, dict):
                        p = att.get("path")
                        if p and any(p.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                            image_paths.append(p)
            
            if (image_paths or input_type_str == "IMAGE") and selected_model == settings.MODEL_GEMMA:
                e_vis = mgr.transition(
                    conversation_id=conv_id,
                    request_id=req_id,
                    new_state=SakiState.VISION,
                    activity="Analyzing visual image content with Gemma 3 Vision",
                    selected_model=selected_model,
                    detected_language=det_lang,
                    capability="VISION"
                )
                pipeline_events.append(e_vis)

            evidence_items = []
            evidence_prompt_block = ""
            evidence_package = None
            research_result_obj = None
            browser_obs_obj = None
            computer_obs_obj = None
            dev_task_obj = None
            git_telemetry_obj = None
            persistent_task_obj = None

            if action and action.requires_world_access:
                tool_name = "GEMINI_SEARCH" if settings.SEARCH_PROVIDER == "gemini" else "DUCKDUCKGO"
                e_search = mgr.transition(
                    conversation_id=conv_id,
                    request_id=req_id,
                    new_state=SakiState.SEARCHING,
                    activity=f"Searching web intelligence via {tool_name}",
                    task=current_task,
                    selected_model=selected_model,
                    detected_language=det_lang,
                    active_tool=tool_name,
                    capability="WORLD_ACCESS",
                    retrieval_status="RECALLING"
                )
                pipeline_events.append(e_search)

                if action.action == "WEB_RESEARCH":
                    from backend.services.research_planner import ResearchPlanner
                    research_result_obj = ResearchPlanner.execute_research(english_input)
                    evidence_package = research_result_obj.evidence_package
                    evidence_items = evidence_package.evidence_items if evidence_package else []
                    evidence_prompt_block = research_result_obj.grounded_prompt_block
                else:
                    from backend.services.web_controller import WebIntelligenceController
                    web_exec_res = WebIntelligenceController.execute(
                        query=english_input,
                        action_decision=action,
                        attachments=attachments
                    )
                    evidence_items = getattr(web_exec_res, "evidence_items", []) if web_exec_res else []
                    evidence_package = getattr(web_exec_res, "evidence_package", None) if web_exec_res else None
                    evidence_prompt_block = getattr(web_exec_res, "grounded_prompt_block", "") if web_exec_res else ""

            # ---------------------------------------------------------
            # STAGE 5: RESPONSE PLANNING & PROMPT ASSEMBLY
            # (Generation happens in English; output translation to the
            # user's language is handled by STAGE 7.5 for reliability.)
            # ---------------------------------------------------------
            user_prefs = [m["content"] for m in memory.get("memories", []) if m.get("type") == "PREFERENCE"]
            plan = plan_response(
                decision.cognitive_state,
                english_input,
                user_preferences=user_prefs,
                support_assessment=decision.support_assessment
            )

            chat_req_wrapper = ChatRequest(
                message=english_input or "Hello",
                conversation_id=conv_id,
                turn_id=turn_id,
                input_type=input_type_str,
                attachments=attachments,
                enable_tts=enable_tts,
                voice=voice_override,
                speed=speed_override,
                is_voice_mode=is_voice_mode
            )
            attachment_ctx = get_attachment_context(chat_req_wrapper)
            prompt_input = english_input + attachment_ctx
            history_context = format_history_context(memory.get("conversation_history", []))

            memory_context = build_smart_memory_context(
                memory=memory,
                query=english_input,
                limit=settings.MEMORY_CONTEXT_LIMIT,
                active_mode=decision.conversation_mode,
                active_project=decision.awareness.current_project if decision.awareness else None
            )
            if evidence_prompt_block:
                memory_context = f"{memory_context}\n\n{evidence_prompt_block}".strip()

            # When the translation pipeline owns the output language, generate in
            # English (stable); otherwise let the model reply natively.
            generation_language = (
                "en"
                if (getattr(settings, "ENABLE_TRANSLATION", True) and det_lang != "en")
                else det_lang
            )

            final_prompt = build_orchestrated_prompt(
                decision,
                plan,
                prompt_input,
                memory_context,
                history_context,
                language=generation_language,
                is_mixed=lang_profile.is_mixed,
                is_voice_mode=is_voice_mode
            )

            # ---------------------------------------------------------
            # STAGE 6: GENERATING (SPECIALIST MODEL INFERENCE)
            # ---------------------------------------------------------
            e_gen = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.GENERATING,
                activity=f"Generating response using {selected_model}",
                task=current_task,
                selected_model=selected_model,
                detected_language=det_lang,
                capability="SPECIALIST_MODEL"
            )
            pipeline_events.append(e_gen)

            raw_response = call_model(
                final_prompt,
                model=selected_model,
                images=image_paths if (image_paths and selected_model == settings.MODEL_GEMMA) else None
            )

            # ---------------------------------------------------------
            # STAGE 7: RESPONSE QUALITY CHECK & REPAIR
            # ---------------------------------------------------------
            e_qc = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.QUALITY_CHECK,
                activity="Performing response quality evaluation, leak check, and grounding review",
                task=current_task,
                selected_model=selected_model,
                detected_language=det_lang
            )
            pipeline_events.append(e_qc)

            eval_result = evaluate_response(
                raw_response,
                plan=plan,
                mode=decision.conversation_mode,
                evidence_items=evidence_items,
                evidence_package=evidence_package,
                action_decision=decision.action_decision if decision else None,
                user_query=english_input
            )

            if eval_result.needs_regeneration:
                try:
                    refined_prompt = final_prompt + "\n[Instruction: Provide a direct, natural, grounded response to the user's situation without preamble.]"
                    retry_response = call_model(
                        refined_prompt,
                        model=selected_model,
                        keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
                        images=image_paths if (image_paths and selected_model == settings.MODEL_GEMMA) else None
                    )
                    retry_eval = evaluate_response(
                        retry_response,
                        plan=plan,
                        mode=decision.conversation_mode,
                        evidence_items=evidence_items,
                        evidence_package=evidence_package,
                        action_decision=decision.action_decision if decision else None,
                        user_query=english_input
                    )
                    if retry_eval.score >= eval_result.score:
                        eval_result = retry_eval
                except Exception as retry_err:
                    print(f"[Brain Engine Controlled Regeneration Error]: {retry_err}")

            final_response_text = eval_result.repaired_text

            # ---------------------------------------------------------
            # STAGE 7.5: OUTPUT TRANSLATION (English → user's language)
            # The stable English answer is translated back into the exact
            # language the user spoke before display, memory, and TTS.
            # ---------------------------------------------------------
            if (
                final_response_text
                and getattr(settings, "ENABLE_TRANSLATION", True)
                and translation_service.needs_translation(det_lang)
            ):
                e_tr_out = mgr.transition(
                    conversation_id=conv_id,
                    request_id=req_id,
                    new_state=SakiState.QUALITY_CHECK,
                    activity=f"Translating response to {target_lang_profile.language_label}",
                    task=current_task,
                    selected_model=selected_model,
                    detected_language=det_lang,
                    details={"translation_direction": "output_to_user_language"}
                )
                pipeline_events.append(e_tr_out)

                final_response_text = translation_service.from_english(
                    final_response_text,
                    det_lang
                )

            # ---------------------------------------------------------
            # STAGE 8: RESPONSE READY & PERSISTENCE
            # ---------------------------------------------------------
            e_ready = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.RESPONSE_READY,
                activity="Admitting to long-term memory and updating conversation history",
                task=current_task,
                selected_model=selected_model,
                detected_language=det_lang
            )
            pipeline_events.append(e_ready)

            from backend.services.memory_admission import MemoryAdmissionEngine, MemoryCandidate, SOURCE_USER, TYPE_PERSONAL_MEMORY
            _web_actions = {"WEB_SEARCH", "WEB_RESEARCH", "WEB_FETCH"}
            _is_web_derived = action and action.action in _web_actions
            _user_wants_memory = any(kw in english_input.lower() for kw in ["remember", "prefer", "like", "building"])

            if _is_web_derived and not _user_wants_memory:
                adm_decision = None
            else:
                adm_candidate = MemoryCandidate(
                    content=user_input,
                    memory_type=TYPE_PERSONAL_MEMORY if _user_wants_memory else "WEB_EVIDENCE",
                    source_type=SOURCE_USER if _user_wants_memory else "WEB"
                )
                adm_decision = MemoryAdmissionEngine.evaluate_candidate(adm_candidate)

            def _dump(obj: Any) -> Any:
                if obj is None:
                    return None
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                if hasattr(obj, "dict"):
                    return obj.dict()
                return obj

            awareness_dict = _dump(decision.awareness) if decision.awareness else None
            if not (_is_web_derived and not _user_wants_memory):
                update_memory(memory, user_input, final_response_text, awareness_dict=awareness_dict)
            append_message_to_conversation(conv_id, user_input, final_response_text, attachments)

            # ---------------------------------------------------------
            # STAGE 9: SPEAKING (TTS SYNTHESIS WHEN VOICE MODE ACTIVE)
            # ---------------------------------------------------------
            tts_telemetry = None
            audio_base64 = None
            has_audio = False

            from backend.services.tts_service import tts_service, normalize_text_for_speech

            if enable_tts and tts_service.enabled:
                e_spk = mgr.transition(
                    conversation_id=conv_id,
                    request_id=req_id,
                    new_state=SakiState.SPEAKING,
                    activity="Synthesizing spoken audio output via TTS engine",
                    task=current_task,
                    selected_model=selected_model,
                    detected_language=det_lang,
                    capability="TEXT_TO_SPEECH"
                )
                pipeline_events.append(e_spk)

                try:
                    clean_for_speech = normalize_text_for_speech(final_response_text)
                    effective_out_lang = getattr(target_lang_profile, "language", None) or det_lang or "en"
                    
                    if effective_out_lang == "te":
                        tts_voice = (voice_override if voice_override and voice_override != tts_service.default_voice else None) or getattr(settings, "SAKI_TTS_VOICE_TE", "te_saki")
                    elif effective_out_lang == "kn":
                        tts_voice = (voice_override if voice_override and voice_override != tts_service.default_voice else None) or getattr(settings, "SAKI_TTS_VOICE_KN", "kn_saki")
                    else:
                        tts_voice = voice_override or getattr(settings, "SAKI_TTS_VOICE_EN", tts_service.default_voice)

                    tts_res = tts_service.synthesize_response(
                        text=clean_for_speech,
                        voice=tts_voice,
                        speed=speed_override or tts_service.default_speed,
                        conversation_id=conv_id,
                        request_id=req_id,
                        language=effective_out_lang
                    )
                    if tts_res.audio_bytes:
                        tts_telemetry = tts_res.to_dict()
                        audio_base64 = f"data:audio/wav;base64,{base64.b64encode(tts_res.audio_bytes).decode('utf-8')}"
                        has_audio = True
                except Exception as tts_err:
                    print(f"[Brain Engine TTS Synthesis Error - Gracefully Preserving Text]: {tts_err}")
                    tts_telemetry = {"error": str(tts_err), "success": False}
                    audio_base64 = None
                    has_audio = False

            # ---------------------------------------------------------
            # STAGE 10: COMPLETED STATE & UNIFIED RESPONSE
            # ---------------------------------------------------------
            e_comp = mgr.transition(
                conversation_id=conv_id,
                request_id=req_id,
                new_state=SakiState.COMPLETED,
                activity="Turn pipeline completed successfully",
                task=current_task,
                selected_model=selected_model,
                detected_language=det_lang
            )
            pipeline_events.append(e_comp)

            response_obj = ChatResponse(
                response=final_response_text,
                intent=decision.task_type,
                mode=decision.conversation_mode,
                routing=_dump(decision),
                awareness=_dump(decision.awareness) if decision.awareness else None,
                plan=ResponsePlanSchema(
                    goal=plan.goal,
                    tone=plan.tone,
                    depth=plan.depth,
                    acknowledge_emotion=plan.acknowledge_emotion,
                    use_humor=plan.use_humor,
                    ask_question=plan.ask_question,
                    technical_detail=plan.technical_detail
                ),
                evaluation=EvaluationResultSchema(
                    passed=eval_result.passed,
                    score=eval_result.score,
                    persona_issues=eval_result.persona_issues
                ),
                action_decision=_dump(decision.action_decision) if decision.action_decision else None,
                world_access_evidence=[EvidenceItemSchema(**_dump(e)) for e in evidence_items] if evidence_items else None,
                evidence_package=EvidencePackageSchema(**_dump(evidence_package)) if evidence_package else None,
                research_result=ResearchResultSchema(**_dump(research_result_obj)) if research_result_obj else None,
                memory_admission=_dump(adm_decision) if adm_decision else None,
                events=[SakiEventSchema(**e.to_dict()) for e in pipeline_events],
                final_state=SakiState.COMPLETED.value,
                tts_telemetry=tts_telemetry,
                audio_base64=audio_base64,
                turn_id=turn_id,
                request_id=req_id,
                conversation_id=conv_id,
                input_type=input_type_str,
                detected_language=det_lang,
                has_audio=has_audio
            )

            turn_deduplicator.complete_turn(conv_id, turn_id, response_obj)
            return response_obj

        except Exception as ex:
            turn_deduplicator.release_turn(conv_id, turn_id)
            err_msg = str(ex)
            print(f"[Brain Engine Execution Error]: {err_msg}")
            traceback.print_exc()
            
            try:
                mgr.transition(
                    conversation_id=conv_id,
                    request_id=req_id,
                    new_state=SakiState.ERROR,
                    activity=f"Turn pipeline encountered error: {err_msg[:80]}",
                    error=err_msg
                )
            except Exception:
                pass

            return ChatResponse(
                response=f"I encountered a temporary issue while processing your request: {err_msg}",
                intent="error",
                mode="casual",
                final_state=SakiState.ERROR.value,
                turn_id=turn_id,
                request_id=req_id,
                conversation_id=conv_id,
                input_type=input_type_str,
                has_audio=False
            )


brain_engine = UnifiedBrainEngine()
