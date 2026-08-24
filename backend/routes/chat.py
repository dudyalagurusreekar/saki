import os
import json
import re
import time
import uuid
import threading
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
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
    PreferenceSchema,
    LearningCandidateSchema,
    WorkflowTelemetrySchema,
    SakiWorkflowSchema,
    WorkflowStepSchema,
    SakiEventSchema
)

from backend.core.events import SakiState, SakiEventType, SakiEvent
from backend.services.event_system import event_manager
from backend.services.ai_service import call_model, stream_model, unload_model
from backend.services.orchestrator import SakiModelOrchestrator, RoutingDecision
from backend.services.emotional_intelligence import SakiAwareness
from backend.services.memory_service import build_smart_memory_context, load_memory, update_memory
from backend.services.response_planner import plan_response, ResponsePlan
from backend.services.response_evaluator import evaluate_response, clean_speaker_tags
from backend.services.learning_service import detect_user_correction
from backend.services.search_service import safe_search
from backend.services.model_manager import model_manager
from backend.services.tts_service import tts_service, TTSLifecycleState, normalize_text_for_speech
from backend.services.vision_service import vision_service
from backend.services.multilingual_service import multilingual_service, LanguageProfile
from backend.services.translation_service import translation_service
from backend.core.config import settings
from backend.core.saki_persona import build_saki_system_prompt, format_prompt_for_model

def detect_query_language(text: str) -> str:
    """Detects ISO language code of user input using MultilingualService, falling back to 'en'."""
    profile = multilingual_service.classify_text(text)
    return profile.language

router = APIRouter()

CONVERSATIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "conversations.json")
_conversations_lock = threading.Lock()


def _load_conversations_data() -> Dict[str, Any]:
    with _conversations_lock:
        if os.path.exists(CONVERSATIONS_FILE):
            try:
                with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    # Initialize from memory.json history if conversations.json doesn't exist
    memory = load_memory()
    history = memory.get("conversation_history", [])
    default_id = "default-session"
    
    init_messages = []
    for h in history:
        if isinstance(h, dict):
            if h.get("user"):
                init_messages.append({"role": "user", "content": h["user"]})
            if h.get("saki"):
                init_messages.append({"role": "assistant", "content": h["saki"]})

    if not init_messages:
        init_messages = [
            {"role": "assistant", "content": "Hey! Good to see you. What are we building or exploring today? ðŸŒ¸"}
        ]

    init_convs = {
        "active_id": default_id,
        "conversations": {
            default_id: {
                "id": default_id,
                "title": "Welcome to Saki",
                "created_at": time.time() - 3600,
                "updated_at": time.time(),
                "messages": init_messages
            }
        }
    }

    _save_conversations_data(init_convs)
    return init_convs


def _save_conversations_data(data: Dict[str, Any]) -> None:
    with _conversations_lock:
        os.makedirs(os.path.dirname(CONVERSATIONS_FILE), exist_ok=True)
        with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def append_message_to_conversation(conv_id: str, user_msg: str, assistant_msg: str, attachments: Optional[List[dict]] = None):
    data = _load_conversations_data()
    convs = data.get("conversations", {})
    
    if conv_id not in convs:
        title = user_msg[:30] + ("..." if len(user_msg) > 30 else "")
        convs[conv_id] = {
            "id": conv_id,
            "title": title or "New Conversation",
            "created_at": time.time(),
            "updated_at": time.time(),
            "messages": []
        }
    
    conv = convs[conv_id]
    conv["updated_at"] = time.time()
    if user_msg:
        conv["messages"].append({"role": "user", "content": user_msg, "attachments": attachments or []})
    if assistant_msg:
        conv["messages"].append({"role": "assistant", "content": assistant_msg})
        
    data["active_id"] = conv_id
    _save_conversations_data(data)


# -------------------------
# CONVERSATION MANAGEMENT ENDPOINTS
# -------------------------
@router.get("/conversations")
def get_conversations():
    data = _load_conversations_data()
    convs = list(data.get("conversations", {}).values())
    convs.sort(key=lambda c: c.get("updated_at", 0), reverse=True)

    now = time.time()
    today_list = []
    yesterday_list = []
    older_list = []

    for c in convs:
        up = c.get("updated_at", now)
        diff_hours = (now - up) / 3600.0
        summary = {
            "id": c.get("id"),
            "title": c.get("title", "Conversation"),
            "updated_at": up,
            "message_count": len(c.get("messages", [])),
            "preview": c.get("messages", [])[-1]["content"][:60] if c.get("messages") else ""
        }
        if diff_hours < 24:
            today_list.append(summary)
        elif diff_hours < 48:
            yesterday_list.append(summary)
        else:
            older_list.append(summary)

    return {
        "active_id": data.get("active_id", "default-session"),
        "today": today_list,
        "yesterday": yesterday_list,
        "older": older_list
    }


@router.get("/conversations/search")
def search_conversations(q: str = Query(..., min_length=1)):
    data = _load_conversations_data()
    q_lower = q.lower().strip()
    results = []

    for c in data.get("conversations", {}).values():
        title = c.get("title", "")
        matches = title.lower().find(q_lower) != -1
        matching_snippet = title

        if not matches:
            for m in c.get("messages", []):
                content = m.get("content", "")
                if q_lower in content.lower():
                    matches = True
                    idx = content.lower().find(q_lower)
                    start = max(0, idx - 20)
                    matching_snippet = "..." + content[start:start + 60] + "..."
                    break

        if matches:
            results.append({
                "id": c.get("id"),
                "title": title,
                "updated_at": c.get("updated_at"),
                "snippet": matching_snippet
            })

    return {"query": q, "results": results}


@router.get("/conversations/{conv_id}")
@router.get("/conversations/{conv_id}/history")
def get_conversation_history(conv_id: str):
    data = _load_conversations_data()
    conv = data.get("conversations", {}).get(conv_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})
    return conv


@router.post("/conversations")
@router.post("/conversations/new")
def create_new_conversation():
    data = _load_conversations_data()
    new_id = f"conv-{uuid.uuid4().hex[:8]}"
    new_conv = {
        "id": new_id,
        "title": "New Conversation",
        "created_at": time.time(),
        "updated_at": time.time(),
        "messages": [
            {"role": "assistant", "content": "Hey! Good to see you. What are we building or exploring today? ðŸŒ¸"}
        ]
    }
    data.setdefault("conversations", {})[new_id] = new_conv
    data["active_id"] = new_id
    _save_conversations_data(data)
    return new_conv


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    data = _load_conversations_data()
    convs = data.get("conversations", {})
    if conv_id in convs:
        del convs[conv_id]
        if data.get("active_id") == conv_id:
            data["active_id"] = next(iter(convs.keys())) if convs else "default-session"
        _save_conversations_data(data)
        return {"deleted": True, "id": conv_id}
    return JSONResponse(status_code=404, content={"error": "Conversation not found"})


# -------------------------
# CHAT PIPELINE HELPERS
# -------------------------
def get_attachment_context(req: ChatRequest) -> str:
    """Helper to analyze uploaded attachments and construct a descriptive text block for the LLM."""
    if not req.attachments:
        return ""
    
    from brain.attachment_analyzer import analyze_attachment
    analyzed_list = []
    for att in req.attachments:
        try:
            analyzed = analyze_attachment(att)
            analyzed_list.append(analyzed)
        except Exception as e:
            print(f"Error analyzing attachment: {e}")
            
    if not analyzed_list:
        return ""
        
    context = "\n\n[Uploaded Files Information]:\n"
    for att in analyzed_list:
        context += f"- Name: {att.name}\n  Type: {att.type}\n  Size: {att.size}\n  Pages/Rows/Files: {att.pages or 1}\n"
        if att.metadata and "error" not in att.metadata:
            context += f"  Metadata: {att.metadata}\n"
    return context


def format_history_context(history: list) -> str:
    """Compile recent conversation turns into context for the prompt."""
    if not history:
        return ""
    formatted = "Recent Conversation:\n"
    for turn in history[-6:]:
        user_turn = turn.get('user', '')
        saki_turn = turn.get('saki', '')
        if user_turn:
            formatted += f"- User: {user_turn}\n"
        if saki_turn:
            formatted += f"- Saki: {saki_turn}\n"
    return formatted


def is_helpless_response(text: str) -> bool:
    """Check if the model response indicates it cannot answer."""
    if not text or len(text.strip()) < 15:
        return True
    text_lower = text.lower()
    helpless_phrases = [
        "i don't know", "i do not know", "not sure", "cannot answer", 
        "unable to answer", "no information available", "apologize, but i cannot",
        "don't have access", "i'm not sure", "cannot find", "sorry, but i don't"
    ]
    return any(phrase in text_lower for phrase in helpless_phrases)


def build_orchestrated_prompt(
    decision: RoutingDecision,
    plan: ResponsePlan,
    prompt_input: str,
    memory_context: str,
    history_context: str,
    language: str = "en",
    is_mixed: bool = False,
    is_voice_mode: bool = False
) -> str:
    assessment = decision.support_assessment
    if assessment:
        emotional_guidance = (
            f"Detected Emotion: {decision.detected_emotion} (intensity {assessment.emotion_intensity}, support need {assessment.support_need})\n"
            f"Support Type: {assessment.support_type.value}\n"
            f"Primary Intent: {assessment.primary_intent}" + (f" | Secondary Intent: {assessment.secondary_intent}" if assessment.secondary_intent else "") + "\n"
            f"Underlying Context: {assessment.cause}\n"
            f"Solution Readiness: {assessment.solution_readiness} (0.0=wants validation/presence, 1.0=wants immediate fix)\n\n"
            f"{plan.directive_prompt}"
        )
    else:
        emotional_guidance = (
            f"Detected Emotion: {decision.detected_emotion} (intensity {decision.emotional_state.intensity})\n"
            f"Cause: {decision.emotional_state.cause}\n"
            f"User Needs: {', '.join(decision.emotional_state.needs)}\n\n"
            f"{plan.directive_prompt}"
        )

    system_prompt = build_saki_system_prompt(
        mode=decision.conversation_mode,
        energy=decision.social_energy.energy,
        warmth=decision.social_energy.warmth,
        playfulness=decision.social_energy.playfulness,
        seriousness=decision.social_energy.seriousness,
        consecutive_frustrations=decision.awareness.consecutive_frustrations if decision.awareness else 0,
        is_breakthrough=(decision.detected_emotion == "celebrating"),
        active_project=decision.awareness.current_project if decision.awareness else None,
        memory_context=memory_context,
        history_context=history_context,
        emotional_guidance=emotional_guidance,
        language=language,
        is_mixed=is_mixed,
        is_voice_mode=is_voice_mode
    )

    return format_prompt_for_model(decision.selected_model, system_prompt, prompt_input)





# -------------------------
# SHARED CHAT PIPELINE (eliminates duplication between /chat and /chat/stream)
# -------------------------
class ChatPipelineResult:
    """Container for all results produced by the shared chat pipeline."""
    __slots__ = [
        'prompt', 'selected_model', 'plan', 'decision', 'memory', 'conv_id',
        'image_paths', 'evidence_items', 'evidence_package', 'research_result_obj',
        'browser_obs_obj', 'computer_obs_obj', 'dev_task_obj', 'git_telemetry_obj',
        'persistent_task_obj', 'active_ctx_items', 'attn_mode', 'unified_rag_pkg',
        'fused_knowledge_pkg', 'knowledge_graph_pkg', 'web_intel_res',
        'adaptive_intel_res', 'wf_telemetry', 'user_input', 'attachments',
        'request_id', 'detected_language', 'pipeline_events', 'visual_analysis',
        'english_input', 'target_language', 'input_translated', 'lang_label',
        'language_mode'
    ]
    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)


def _execute_chat_pipeline(req: ChatRequest) -> ChatPipelineResult:
    """
    Shared pipeline for both /chat and /chat/stream.
    Gates heavyweight subsystems behind action_decision to avoid running
    RAG, knowledge fusion, web intelligence, workflows etc. for simple messages.
    """
    result = ChatPipelineResult()
    user_input = req.message.strip()
    conv_id = req.conversation_id or "default-session"
    request_id = getattr(req, "request_id", None) or f"req_{uuid.uuid4().hex[:12]}"
    attachment_context = get_attachment_context(req)
    prompt_input = user_input + attachment_context

    result.user_input = user_input
    result.conv_id = conv_id
    result.request_id = request_id
    result.attachments = req.attachments
    pipeline_events: List[SakiEvent] = []
    result.pipeline_events = pipeline_events

    # 1. Start request tracking & detect language
    event_manager.start_request(conv_id, request_id)
    lang_profile = multilingual_service.classify_text(user_input)
    lang = lang_profile.language
    result.detected_language = lang

    # State: PROCESSING
    e_proc = event_manager.transition(
        conversation_id=conv_id,
        request_id=request_id,
        new_state=SakiState.PROCESSING,
        activity="Evaluating request intent and classifying conversation mode",
        detected_language=lang,
        details={
            "message_length": len(user_input),
            "has_attachments": bool(req.attachments),
            "language_label": lang_profile.language_label,
            "is_mixed": lang_profile.is_mixed,
            "language_confidence": lang_profile.confidence
        }
    )
    pipeline_events.append(e_proc)

    # 1.5 STABLE CORE FLOW: translate non-English input to English.
    # All routing, memory retrieval, and generation run on English text
    # exactly like normal chat; the answer is translated back to the
    # user's language before display and TTS.
    english_input = user_input
    input_translated = False
    target_language = lang
    lang_label = lang_profile.language_label
    if (
        user_input
        and getattr(settings, "ENABLE_TRANSLATION", True)
        and translation_service.needs_translation(lang)
    ):
        e_tr_in = event_manager.transition(
            conversation_id=conv_id,
            request_id=request_id,
            new_state=SakiState.PROCESSING,
            activity=f"Translating input from {lang_profile.language_label} to English",
            detected_language=lang,
            details={"translation_direction": "input_to_english"}
        )
        pipeline_events.append(e_tr_in)

        english_input = translation_service.to_english(user_input, source_lang=lang)
        input_translated = english_input != user_input

    result.english_input = english_input
    result.input_translated = input_translated
    result.target_language = target_language
    result.lang_label = lang_label

    # Downstream processing (prompt, routing, memory) uses English text
    prompt_input = english_input + attachment_context

    memory = load_memory()
    result.memory = memory
    history_context = format_history_context(memory.get("conversation_history", []))

    # Check for user correction (Learning Loop) — English-normalized text
    correction = detect_user_correction(english_input)
    if correction:
        from backend.services.memory_service import _upsert_memory
        _upsert_memory(memory, correction)

    prev_awareness_raw = memory.get("awareness")
    prev_awareness = SakiAwareness(**prev_awareness_raw) if prev_awareness_raw else None
    active_proj = prev_awareness.current_project if prev_awareness else "Saki"

    # State: REMEMBERING
    e_rem = event_manager.transition(
        conversation_id=conv_id,
        request_id=request_id,
        new_state=SakiState.REMEMBERING,
        activity=f"Building personal context and recalling memories for project '{active_proj}'",
        detected_language=lang,
        retrieval_status="RECALLING",
        memory_usage={
            "history_turns": len(memory.get("conversation_history", [])),
            "durable_memories": len(memory.get("memories", []))
        }
    )
    pipeline_events.append(e_rem)

    # Model Orchestration — lightweight, always runs
    is_voice = bool(getattr(req, "is_voice_mode", False) or getattr(req, "enable_tts", False))
    recent_turns = memory.get("conversation_history", [])
    decision = SakiModelOrchestrator.classify_request(
        query=english_input,
        attachments=req.attachments,
        previous_awareness=prev_awareness,
        memory_data=memory,
        is_voice_mode=is_voice,
        recent_history=recent_turns
    )
    result.decision = decision
    action = decision.action_decision
    selected_model = decision.selected_model
    result.selected_model = selected_model
    current_task = decision.cognitive_state.conversation.task

    # -------------------------------------------------------
    # GATED SUBSYSTEMS: Only run what the orchestrator decided
    # -------------------------------------------------------

    # 1. World Access / Research / Browser (only if action requires it)
    evidence_items = []
    evidence_prompt_block = ""
    evidence_package = None
    research_result_obj = None
    browser_obs_obj = None
    if action and action.requires_world_access:
        tool_name = "GEMINI_SEARCH" if settings.SEARCH_PROVIDER == "gemini" else "DUCKDUCKGO"
        e_search = event_manager.transition(
            conversation_id=conv_id,
            request_id=request_id,
            new_state=SakiState.SEARCHING,
            activity=f"Searching web intelligence via {tool_name}",
            task=current_task,
            selected_model=selected_model,
            detected_language=lang,
            active_tool=tool_name,
            capability="WORLD_ACCESS",
            retrieval_status="RECALLING"
        )
        pipeline_events.append(e_search)

        from backend.services.world_access_manager import WorldAccessManager
        if action.action in ["BROWSER_READ", "BROWSER_INTERACT"]:
            from backend.services.browser_controller import BrowserController, BrowserAction
            url_match = re.search(r"https?://[^\s]+", english_input)
            target_url = url_match.group(0) if url_match else "https://duckduckgo.com"
            b_action = BrowserAction(action_type=action.action, url=target_url)
            browser_obs_obj = BrowserController.execute_action(b_action)
            evidence_prompt_block = browser_obs_obj.grounded_prompt_block
        elif action.action == "WEB_RESEARCH":
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
                attachments=req.attachments
            )
            evidence_items = web_exec_res.evidence_items
            evidence_prompt_block = web_exec_res.grounded_prompt_block
            evidence_package = web_exec_res.evidence_package

        # Apply relevance checks and mode directives for search capabilities
        if action.action in ["WEB_SEARCH", "WEB_RESEARCH", "WEB_FETCH"]:
            is_insufficient = (
                not evidence_items or 
                not evidence_package or 
                evidence_package.evidence_status == "INSUFFICIENT"
            )
            
            if is_insufficient:
                evidence_items = []
                evidence_package = None
                evidence_prompt_block = (
                    "\n\n<external_web_content>\n"
                    "NOTE: Web search returned no relevant results or insufficient verified information about this request.\n"
                    "</external_web_content>\n\n"
                    "[CRITICAL DIRECTIVE: You MUST state that you do not have verified records or active web search results to answer this query. Refuse to guess, speculate, or extrapolate. Speak naturally as Saki and explain you couldn't retrieve enough information.]"
                )
            else:
                is_verification = (action and action.query_intent == "verification") or any(re.search(pat, english_input.lower()) for pat in [
                    r"\b(verify|confirm|check whether|check if)\b",
                    r"\bis this correct\b",
                    r"\bis this true\b",
                    r"\bgive me verified\b"
                ])
                if is_verification:
                    evidence_prompt_block = (
                        f"{evidence_prompt_block}\n\n"
                        f"[VERIFICATION DIRECTIVE: The user explicitly asked you to verify information. "
                        f"Perform deep source comparison, point out any conflicting data, cite the source domains, "
                        f"and provide a verified response based strictly on the retrieved sources.]"
                    )
                else:
                    evidence_prompt_block = (
                        f"{evidence_prompt_block}\n\n"
                        f"[FACTUAL DIRECTIVE: Answer naturally as Saki using the facts from the retrieved sources. "
                        f"Keep it direct and conversational. Do not mention that you did verification unless specifically requested.]"
                    )

    if evidence_prompt_block:
        prompt_input = prompt_input + evidence_prompt_block
    result.evidence_items = evidence_items
    result.evidence_package = evidence_package
    result.research_result_obj = research_result_obj
    result.browser_obs_obj = browser_obs_obj

    # 2. Computer / Development / Git (only if CODING action)
    computer_obs_obj = None
    dev_task_obj = None
    git_telemetry_obj = None
    persistent_task_obj = None
    if action and action.action == "CODING":
        e_acting = event_manager.transition(
            conversation_id=conv_id,
            request_id=request_id,
            new_state=SakiState.ACTING,
            activity="Inspecting local workspace and executing coding capability",
            task=current_task,
            selected_model=selected_model,
            detected_language=lang,
            active_tool="CODE_EXEC",
            capability="DEVELOPMENT"
        )
        pipeline_events.append(e_acting)

        from backend.services.computer_controller import ComputerController, ComputerAction
        from backend.services.development_capability import DevelopmentCapability
        from backend.services.git_github_capability import GitGitHubCapability
        c_action = ComputerAction(action_type="INSPECT_WORKSPACE", target_path=settings.WORKSPACE_ROOT)
        computer_obs_obj = ComputerController.execute_action(c_action)
        dev_task_obj = DevelopmentCapability.execute_development_task(english_input)
        git_telemetry_obj = GitGitHubCapability.execute_action("GIT_STATUS")
    result.computer_obs_obj = computer_obs_obj
    result.dev_task_obj = dev_task_obj
    result.git_telemetry_obj = git_telemetry_obj

    # 3. Persistent Tasks (only if keywords match)
    if any(k in english_input.lower() for k in ["schedule task", "monitor ci", "remind me", "recurring task"]):
        from backend.services.task_capability import PersistentTaskCapability, SCHEDULE_CONDITION
        persistent_task_obj = PersistentTaskCapability.create_task(english_input, schedule_type=SCHEDULE_CONDITION, condition="CI_STATUS == SUCCESS")
    result.persistent_task_obj = persistent_task_obj

    # 4. Knowledge subsystems â€” GATED: only run for non-trivial queries
    from backend.services.personal_context import PersonalContextEngine, AttentionPolicy
    active_ctx_items = PersonalContextEngine.select_minimal_context(english_input)
    attn_mode = PersonalContextEngine.evaluate_proactive_attention(AttentionPolicy())
    result.active_ctx_items = active_ctx_items
    result.attn_mode = attn_mode

    # Only run heavyweight RAG/fusion/graph for queries that actually need knowledge
    english_lower = english_input.lower()
    needs_knowledge = (action and action.action in ["CODING", "WEB_SEARCH", "WEB_RESEARCH", "WEB_FETCH"]) or \
        any(k in english_lower for k in ["how", "what", "why", "explain", "compare", "build", "fix", "error", "implement", "design", "architecture"])

    unified_rag_pkg = None
    fused_knowledge_pkg = None
    knowledge_graph_pkg = None
    web_intel_res = None
    adaptive_intel_res = None
    wf_telemetry = None

    if needs_knowledge:
        from backend.services.unified_knowledge import UnifiedKnowledgeEngine
        from backend.services.knowledge_fusion import KnowledgeFusionEngine
        from backend.services.knowledge_graph import KnowledgeGraphEngine
        unified_rag_pkg = UnifiedKnowledgeEngine.retrieve_knowledge(english_input, web_evidence_items=evidence_items)
        fused_knowledge_pkg = KnowledgeFusionEngine.fuse_knowledge(unified_rag_pkg)
        knowledge_graph_pkg = KnowledgeGraphEngine.traverse_subgraph(english_input, fused_knowledge_pkg)

    if (action and action.requires_world_access) or any(k in english_lower for k in ["search", "web", "latest", "doc", "fastapi"]):
        from backend.services.web_intelligence import WebIntelligenceCapability
        web_intel_res = WebIntelligenceCapability.execute_web_intelligence(
            english_input,
            evidence_package=evidence_package,
            evidence_items=evidence_items
        )

    # Adaptive intelligence â€” lightweight, always runs
    from backend.services.adaptive_intelligence import AdaptiveIntelligenceEngine
    adaptive_intel_res = AdaptiveIntelligenceEngine.process_user_input(english_input)

    # Autonomous workflows â€” only if keywords match
    if any(k in english_lower for k in ["workflow", "prepare a fix", "multi-step"]):
        from backend.services.autonomous_workflow import AutonomousWorkflowEngine
        created_wf = AutonomousWorkflowEngine.create_workflow(english_input)
        wf_telemetry = AutonomousWorkflowEngine.execute_workflow(created_wf.workflow_id)

    result.unified_rag_pkg = unified_rag_pkg
    result.fused_knowledge_pkg = fused_knowledge_pkg
    result.knowledge_graph_pkg = knowledge_graph_pkg
    result.web_intel_res = web_intel_res
    result.adaptive_intel_res = adaptive_intel_res
    result.wf_telemetry = wf_telemetry

    # Extract image paths for vision models & multimodal processing
    image_paths = []
    if req.attachments:
        for att in req.attachments:
            if att.get("path") and (
                att.get("type") == "image"
                or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            ):
                image_paths.append(att["path"])
    result.image_paths = image_paths

    vis_res = None
    if image_paths or getattr(decision, "vision_required", False):
        if image_paths:
            vis_res = vision_service.analyze_image(
                image_paths[0],
                user_query=english_input,
                task_type=decision.task_type
            )
            result.visual_analysis = vis_res
            if vis_res.success:
                prompt_input += f"\n\n{vis_res.to_context_string()}"

        e_vis = event_manager.transition(
            conversation_id=conv_id,
            request_id=request_id,
            new_state=SakiState.VISION,
            activity=f"Inspecting visual attachment via Gemma 3 4B",
            task=current_task,
            selected_model=settings.MODEL_GEMMA,
            detected_language=lang,
            active_tool="GEMMA3_VISION",
            capability="VISION",
            details={
                "image_count": len(image_paths),
                "has_ocr_text": bool(vis_res and vis_res.detected_text),
                "ui_elements_count": len(vis_res.ui_elements) if vis_res else 0,
                "errors_detected_count": len(vis_res.errors_detected) if vis_res else 0,
                "vision_latency_ms": round(vis_res.latency_ms, 1) if vis_res else 0.0,
                "image_format": vis_res.image_metadata.format if (vis_res and vis_res.image_metadata) else None,
                "image_resolution": f"{vis_res.image_metadata.processed_width}x{vis_res.image_metadata.processed_height}" if (vis_res and vis_res.image_metadata) else None,
                "success": vis_res.success if vis_res else False
            }
        )
        pipeline_events.append(e_vis)

    # Build prompt and plan (generation in English when the translation
    # pipeline owns the output language; STAGE in chat_stream translates back)
    user_prefs = [m["content"] for m in memory.get("memories", []) if m.get("type") == "PREFERENCE"]
    plan = plan_response(
        decision.cognitive_state, 
        english_input, 
        user_preferences=user_prefs,
        support_assessment=decision.support_assessment
    )
    result.plan = plan

    memory_context = build_smart_memory_context(
        memory=memory,
        query=english_input,
        limit=settings.MEMORY_CONTEXT_LIMIT,
        active_mode=decision.conversation_mode,
        active_project=decision.awareness.current_project if decision.awareness else None
    )

    generation_language = (
        "en"
        if (getattr(settings, "ENABLE_TRANSLATION", True) and target_language != "en")
        else target_language
    )

    prompt = build_orchestrated_prompt(
        decision, 
        plan, 
        prompt_input, 
        memory_context, 
        history_context,
        language=generation_language,
        is_mixed=lang_profile.is_mixed,
        is_voice_mode=is_voice
    )
    result.prompt = prompt
    result.selected_model = decision.selected_model

    # State: THINKING
    e_think = event_manager.transition(
        conversation_id=conv_id,
        request_id=request_id,
        new_state=SakiState.THINKING,
        activity=f"Reasoning with model {selected_model}",
        task=current_task,
        selected_model=selected_model,
        detected_language=lang
    )
    pipeline_events.append(e_think)

    return result


# -------------------------
# STREAMING CHAT
# -------------------------
@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    p = _execute_chat_pipeline(req)

    def generate():
        # 1. Yield all preceding pipeline setup events
        for evt in p.pipeline_events:
            yield evt.to_sse()

        action = p.decision.action_decision if p.decision else None
        requires_web = bool(action and getattr(action, "requires_world_access", False))
        freshness = getattr(action, "freshness_requirement", "STABLE") if action else "STABLE"
        is_cef = (
            freshness == "CURRENT_EXTERNAL_FACT" or
            getattr(action, "query_intent", "") == "current_external_fact"
        )
        is_insufficient = requires_web and (
            not p.evidence_items or 
            not p.evidence_package or 
            getattr(p.evidence_package, "evidence_status", "") == "INSUFFICIENT"
        )

        # CURRENT_EXTERNAL_FACT Gate: If normal web search failed for a current fact query,
        # escalate to Gemini immediately rather than streaming hallucinated static knowledge.
        if (is_cef or (requires_web and is_insufficient)):
            from backend.services.gemini_escalation import GeminiEscalationEngine
            already_attempted = getattr(req, "gemini_final_escalation_attempted", False)
            if not already_attempted and is_insufficient:
                e_esc = event_manager.transition(
                    conversation_id=p.conv_id,
                    request_id=p.request_id,
                    new_state=SakiState.SEARCHING,
                    activity="Escalating query to Gemini Grounded Search",
                    selected_model="gemini-2.5-flash",
                    active_tool="GEMINI_ESCALATION",
                    capability="WORLD_ACCESS"
                )
                yield e_esc.to_sse()

                gemini_text, esc_status, esc_latency = GeminiEscalationEngine.escalate_to_gemini(
                    user_query=p.user_input,
                    timeout=15.0
                )
                if gemini_text and len(gemini_text.strip()) > 10:
                    final_response = gemini_text.strip()
                else:
                    final_response = "I'm sorry, but I wasn't able to retrieve verified current information to answer your question right now."

                # Stable core flow: answer arrives in English → translate to user's language
                if getattr(settings, "ENABLE_TRANSLATION", True) and (p.target_language or "en") != "en":
                    final_response = translation_service.from_english(final_response, p.target_language)
                
                ft_ms = event_manager.record_first_token(p.request_id)
                e_spk = event_manager.transition(
                    conversation_id=p.conv_id,
                    request_id=p.request_id,
                    new_state=SakiState.SPEAKING,
                    activity="Streaming verified escalation response",
                    selected_model="gemini-2.5-flash"
                )
                yield e_spk.to_sse()

                tok_evt = SakiEvent(
                    event_type=SakiEventType.TOKEN,
                    conversation_id=p.conv_id,
                    request_id=p.request_id,
                    state=SakiState.SPEAKING,
                    selected_model="gemini-2.5-flash",
                    details={"chunk": final_response}
                )
                yield tok_evt.to_sse()

                awareness_dict = p.decision.awareness.dict() if p.decision.awareness else None
                update_memory(p.memory, p.user_input, final_response, awareness_dict=awareness_dict)
                append_message_to_conversation(p.conv_id, p.user_input, final_response, p.attachments)

                e_idle = event_manager.transition(
                    conversation_id=p.conv_id,
                    request_id=p.request_id,
                    new_state=SakiState.IDLE,
                    activity="Ready for next turn"
                )
                yield e_idle.to_sse()
                return

        # Stable core flow control: when the user's language is non-English,
        # stream silently into a buffer; the finished English answer is
        # evaluated, translated to the user's language, then emitted.
        target_lang = p.target_language or "en"
        translate_out = bool(
            getattr(settings, "ENABLE_TRANSLATION", True)
            and target_lang != "en"
            and p.input_translated
        )

        full_response = ""
        prefix_buffer = ""
        prefix_checked = False
        speaking_emitted = False

        try:
            for chunk in stream_model(
                p.prompt,
                model=p.selected_model,
                keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
                images=p.image_paths if (p.image_paths and p.selected_model == settings.MODEL_GEMMA) else None
            ):
                full_response += chunk

                if not speaking_emitted:
                    event_manager.record_first_token(p.request_id)
                    e_spk = event_manager.transition(
                        conversation_id=p.conv_id,
                        request_id=p.request_id,
                        new_state=SakiState.SPEAKING,
                        activity=(
                            f"Generating response via {p.selected_model} (will translate to {p.lang_label or target_lang})"
                            if translate_out else f"Streaming response from {p.selected_model}"
                        ),
                        selected_model=p.selected_model
                    )
                    yield e_spk.to_sse()
                    speaking_emitted = True

                if translate_out:
                    continue  # buffer English output; translated text is emitted below

                if not prefix_checked:
                    prefix_buffer += chunk
                    if len(prefix_buffer) > 20 or "\n" in prefix_buffer or " " in prefix_buffer:
                        cleaned_buffer = re.sub(r"^(?:saki|assistant|ai|\[saki\]|\[assistant\])\s*[-:：]?\s*", "", prefix_buffer, flags=re.IGNORECASE)
                        prefix_checked = True
                        if cleaned_buffer:
                            tok_evt = SakiEvent(
                                event_type=SakiEventType.TOKEN,
                                conversation_id=p.conv_id,
                                request_id=p.request_id,
                                state=SakiState.SPEAKING,
                                selected_model=p.selected_model,
                                details={"chunk": cleaned_buffer}
                            )
                            yield tok_evt.to_sse()
                else:
                    tok_evt = SakiEvent(
                        event_type=SakiEventType.TOKEN,
                        conversation_id=p.conv_id,
                        request_id=p.request_id,
                        state=SakiState.SPEAKING,
                        selected_model=p.selected_model,
                        details={"chunk": chunk}
                    )
                    yield tok_evt.to_sse()

            if not prefix_checked and prefix_buffer and not translate_out:
                cleaned_buffer = re.sub(r"^(?:saki|assistant|ai|\[saki\]|\[assistant\])\s*[-:：]?\s*", "", prefix_buffer, flags=re.IGNORECASE)
                if cleaned_buffer:
                    tok_evt = SakiEvent(
                        event_type=SakiEventType.TOKEN,
                        conversation_id=p.conv_id,
                        request_id=p.request_id,
                        state=SakiState.SPEAKING,
                        selected_model=p.selected_model,
                        details={"chunk": cleaned_buffer}
                    )
                    yield tok_evt.to_sse()

            eval_result = evaluate_response(
                full_response,
                plan=p.plan,
                mode=p.decision.conversation_mode,
                evidence_items=p.evidence_items,
                evidence_package=p.evidence_package,
                action_decision=p.decision.action_decision if p.decision else None,
                user_query=p.user_input
            )
            cleaned_response = eval_result.repaired_text

            # STABLE CORE FLOW: translate the finished English answer back
            # into the user's spoken language before display, memory, and TTS.
            final_text = cleaned_response
            if translate_out and cleaned_response and full_response.strip():
                e_tr_out = event_manager.transition(
                    conversation_id=p.conv_id,
                    request_id=p.request_id,
                    new_state=SakiState.QUALITY_CHECK,
                    activity=f"Translating response to {p.lang_label or target_lang}",
                    selected_model=p.selected_model,
                    detected_language=target_lang,
                    details={"translation_direction": "output_to_user_language"}
                )
                yield e_tr_out.to_sse()

                final_text = translation_service.from_english(cleaned_response, target_lang)

                # Emit the translated answer as natural token chunks
                pieces = re.findall(r"\S+\s*", final_text)
                out_buffer = ""
                for piece in pieces:
                    out_buffer += piece
                    if len(out_buffer) >= 80:
                        tok_evt = SakiEvent(
                            event_type=SakiEventType.TOKEN,
                            conversation_id=p.conv_id,
                            request_id=p.request_id,
                            state=SakiState.SPEAKING,
                            selected_model=p.selected_model,
                            details={"chunk": out_buffer}
                        )
                        yield tok_evt.to_sse()
                        out_buffer = ""
                if out_buffer:
                    tok_evt = SakiEvent(
                        event_type=SakiEventType.TOKEN,
                        conversation_id=p.conv_id,
                        request_id=p.request_id,
                        state=SakiState.SPEAKING,
                        selected_model=p.selected_model,
                        details={"chunk": out_buffer}
                    )
                    yield tok_evt.to_sse()

            awareness_dict = p.decision.awareness.dict() if p.decision.awareness else None
            update_memory(p.memory, p.user_input, final_text, awareness_dict=awareness_dict)
            append_message_to_conversation(p.conv_id, p.user_input, final_text, p.attachments)

            if getattr(req, "enable_tts", False) and tts_service.enabled:
                try:
                    # Language-aware voice selection (mirrors brain engine)
                    if target_lang == "te":
                        tts_voice = getattr(req, "voice", None) or getattr(settings, "SAKI_TTS_VOICE_TE", "te_saki")
                    elif target_lang == "kn":
                        tts_voice = getattr(req, "voice", None) or getattr(settings, "SAKI_TTS_VOICE_KN", "kn_saki")
                    else:
                        tts_voice = getattr(req, "voice", None) or getattr(settings, "SAKI_TTS_VOICE_EN", tts_service.default_voice)

                    tts_res = tts_service.synthesize_response(
                        text=normalize_text_for_speech(final_text),
                        voice=tts_voice,
                        speed=getattr(req, "speed", None) or tts_service.default_speed,
                        conversation_id=p.conv_id,
                        request_id=p.request_id,
                        language=target_lang
                    )
                    import base64
                    b64_audio = base64.b64encode(tts_res.audio_bytes).decode('utf-8')
                    audio_payload = tts_res.to_dict()
                    audio_payload["audio_base64"] = f"data:audio/wav;base64,{b64_audio}"

                    tts_evt = SakiEvent(
                        event_type=SakiEventType.STATUS,
                        conversation_id=p.conv_id,
                        request_id=p.request_id,
                        state=SakiState.SPEAKING,
                        activity="TTS audio synthesis ready",
                        active_tool=f"{tts_res.provider.upper()}_TTS",
                        capability="VOICE_SYNTHESIS",
                        detected_language=target_lang,
                        details={"tts_audio": audio_payload}
                    )
                    yield tts_evt.to_sse()
                except Exception as tts_err:
                    print(f"[TTS Stream Synthesis Non-Fatal Error]: {tts_err}")

            e_idle = event_manager.transition(
                conversation_id=p.conv_id,
                request_id=p.request_id,
                new_state=SakiState.IDLE,
                activity="Ready for next turn",
                details={"total_chars": len(final_text)}
            )
            yield e_idle.to_sse()

        except Exception as e:
            e_err = event_manager.transition(
                conversation_id=p.conv_id,
                request_id=p.request_id,
                new_state=SakiState.ERROR,
                activity="Streaming execution error",
                error=str(e)
            )
            yield e_err.to_sse()
            event_manager.transition(
                conversation_id=p.conv_id,
                request_id=p.request_id,
                new_state=SakiState.IDLE,
                activity="Reset to idle after error"
            )

    return StreamingResponse(generate(), media_type="text/event-stream")




@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Unified Chat Endpoint.
    Delegates all turns to the central Unified Saki Brain Engine.
    """
    from backend.services.brain_engine import brain_engine
    return brain_engine.execute_turn(req)






@router.post("/chat/unload")
def chat_unload(model_name: Optional[str] = None):
    target_model = model_name or settings.MODEL_DEFAULT
    success = unload_model(target_model)
    return {
        "unloaded_model": target_model,
        "success": success
    }


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_filename = os.path.basename(file.filename or "upload")
    upload_dir = os.path.abspath(os.path.join(os.getcwd(), "data", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)
    
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        return JSONResponse(
            status_code=400,
            content={"error": "File size exceeds 15MB maximum limit."}
        )

    ext = os.path.splitext(safe_filename)[1].lower()
    is_image = ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
    img_meta = None

    if is_image:
        valid, err_msg, img_meta = vision_service.validate_image_bytes(content, filename=safe_filename)
        if not valid:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid or corrupted image: {err_msg}"}
            )

    with open(file_path, "wb") as f:
        f.write(content)
        
    res_data = {
        "name": safe_filename,
        "path": file_path,
        "size": len(content),
        "type": "image" if is_image else "file"
    }
    if img_meta:
        res_data["format"] = img_meta.format
        res_data["width"] = img_meta.original_width
        res_data["height"] = img_meta.original_height

    return res_data
