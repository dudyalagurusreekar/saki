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
    WorkflowStepSchema
)

from backend.services.ai_service import call_model, stream_model, unload_model
from backend.services.orchestrator import SakiModelOrchestrator, RoutingDecision
from backend.services.emotional_intelligence import SakiAwareness
from backend.services.memory_service import build_smart_memory_context, load_memory, update_memory
from backend.services.response_planner import plan_response, ResponsePlan
from backend.services.response_evaluator import evaluate_response, clean_speaker_tags
from backend.services.learning_service import detect_user_correction
from backend.services.search_service import safe_search
from backend.services.model_manager import model_manager
from backend.core.config import settings
from backend.core.saki_persona import build_saki_system_prompt

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
def get_conversation_history(conv_id: str):
    data = _load_conversations_data()
    conv = data.get("conversations", {}).get(conv_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})
    return conv


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
    history_context: str
) -> str:
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
        emotional_guidance=emotional_guidance
    )

    return f"{system_prompt}\n\nUser: {prompt_input}\nSaki:"





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
        'adaptive_intel_res', 'wf_telemetry', 'user_input', 'attachments'
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
    attachment_context = get_attachment_context(req)
    prompt_input = user_input + attachment_context

    result.user_input = user_input
    result.conv_id = conv_id
    result.attachments = req.attachments

    memory = load_memory()
    result.memory = memory
    history_context = format_history_context(memory.get("conversation_history", []))

    # Check for user correction (Learning Loop)
    correction = detect_user_correction(user_input)
    if correction:
        from backend.services.memory_service import _upsert_memory
        _upsert_memory(memory, correction)

    prev_awareness_raw = memory.get("awareness")
    prev_awareness = SakiAwareness(**prev_awareness_raw) if prev_awareness_raw else None

    # Model Orchestration â€” lightweight, always runs
    decision = SakiModelOrchestrator.classify_request(
        query=user_input,
        attachments=req.attachments,
        previous_awareness=prev_awareness,
        memory_data=memory
    )
    result.decision = decision
    action = decision.action_decision

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
        from backend.services.world_access_manager import WorldAccessManager
        if action.action in ["BROWSER_READ", "BROWSER_INTERACT"]:
            from backend.services.browser_controller import BrowserController, BrowserAction
            url_match = re.search(r"https?://[^\s]+", user_input)
            target_url = url_match.group(0) if url_match else "https://duckduckgo.com"
            b_action = BrowserAction(action_type=action.action, url=target_url)
            browser_obs_obj = BrowserController.execute_action(b_action)
            evidence_prompt_block = browser_obs_obj.grounded_prompt_block
        elif action.action == "WEB_RESEARCH":
            from backend.services.research_planner import ResearchPlanner
            research_result_obj = ResearchPlanner.execute_research(user_input)
            evidence_package = research_result_obj.evidence_package
            evidence_items = evidence_package.evidence_items if evidence_package else []
            evidence_prompt_block = research_result_obj.grounded_prompt_block
        else:
            from backend.services.web_controller import WebIntelligenceController
            web_exec_res = WebIntelligenceController.execute(
                query=user_input,
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
                is_verification = (action and action.query_intent == "verification") or any(re.search(pat, user_input.lower()) for pat in [
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
        from backend.services.computer_controller import ComputerController, ComputerAction
        from backend.services.development_capability import DevelopmentCapability
        from backend.services.git_github_capability import GitGitHubCapability
        c_action = ComputerAction(action_type="INSPECT_WORKSPACE", target_path=settings.WORKSPACE_ROOT)
        computer_obs_obj = ComputerController.execute_action(c_action)
        dev_task_obj = DevelopmentCapability.execute_development_task(user_input)
        git_telemetry_obj = GitGitHubCapability.execute_action("GIT_STATUS")
    result.computer_obs_obj = computer_obs_obj
    result.dev_task_obj = dev_task_obj
    result.git_telemetry_obj = git_telemetry_obj

    # 3. Persistent Tasks (only if keywords match)
    if any(k in user_input.lower() for k in ["schedule task", "monitor ci", "remind me", "recurring task"]):
        from backend.services.task_capability import PersistentTaskCapability, SCHEDULE_CONDITION
        persistent_task_obj = PersistentTaskCapability.create_task(user_input, schedule_type=SCHEDULE_CONDITION, condition="CI_STATUS == SUCCESS")
    result.persistent_task_obj = persistent_task_obj

    # 4. Knowledge subsystems â€” GATED: only run for non-trivial queries
    from backend.services.personal_context import PersonalContextEngine, AttentionPolicy
    active_ctx_items = PersonalContextEngine.select_minimal_context(user_input)
    attn_mode = PersonalContextEngine.evaluate_proactive_attention(AttentionPolicy())
    result.active_ctx_items = active_ctx_items
    result.attn_mode = attn_mode

    # Only run heavyweight RAG/fusion/graph for queries that actually need knowledge
    user_lower = user_input.lower()
    needs_knowledge = (action and action.action in ["CODING", "WEB_SEARCH", "WEB_RESEARCH", "WEB_FETCH"]) or \
        any(k in user_lower for k in ["how", "what", "why", "explain", "compare", "build", "fix", "error", "implement", "design", "architecture"])

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
        unified_rag_pkg = UnifiedKnowledgeEngine.retrieve_knowledge(user_input, web_evidence_items=evidence_items)
        fused_knowledge_pkg = KnowledgeFusionEngine.fuse_knowledge(unified_rag_pkg)
        knowledge_graph_pkg = KnowledgeGraphEngine.traverse_subgraph(user_input, fused_knowledge_pkg)

    if (action and action.requires_world_access) or any(k in user_lower for k in ["search", "web", "latest", "doc", "fastapi"]):
        from backend.services.web_intelligence import WebIntelligenceCapability
        web_intel_res = WebIntelligenceCapability.execute_web_intelligence(
            user_input,
            evidence_package=evidence_package,
            evidence_items=evidence_items
        )

    # Adaptive intelligence â€” lightweight, always runs
    from backend.services.adaptive_intelligence import AdaptiveIntelligenceEngine
    adaptive_intel_res = AdaptiveIntelligenceEngine.process_user_input(user_input)

    # Autonomous workflows â€” only if keywords match
    if any(k in user_lower for k in ["workflow", "prepare a fix", "multi-step"]):
        from backend.services.autonomous_workflow import AutonomousWorkflowEngine
        created_wf = AutonomousWorkflowEngine.create_workflow(user_input)
        wf_telemetry = AutonomousWorkflowEngine.execute_workflow(created_wf.workflow_id)

    result.unified_rag_pkg = unified_rag_pkg
    result.fused_knowledge_pkg = fused_knowledge_pkg
    result.knowledge_graph_pkg = knowledge_graph_pkg
    result.web_intel_res = web_intel_res
    result.adaptive_intel_res = adaptive_intel_res
    result.wf_telemetry = wf_telemetry

    # Build prompt and plan
    user_prefs = [m["content"] for m in memory.get("memories", []) if m.get("type") == "PREFERENCE"]
    plan = plan_response(decision.cognitive_state, user_input, user_preferences=user_prefs)
    result.plan = plan

    memory_context = build_smart_memory_context(
        memory=memory,
        query=user_input,
        limit=settings.MEMORY_CONTEXT_LIMIT,
        active_mode=decision.conversation_mode,
        active_project=decision.awareness.current_project if decision.awareness else None
    )

    prompt = build_orchestrated_prompt(decision, plan, prompt_input, memory_context, history_context)
    result.prompt = prompt
    result.selected_model = decision.selected_model

    # Extract image paths for vision models
    image_paths = []
    if req.attachments:
        for att in req.attachments:
            if att.get("path") and (
                att.get("type") == "image"
                or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            ):
                image_paths.append(att["path"])
    result.image_paths = image_paths

    return result


# -------------------------
# STREAMING CHAT
# -------------------------
@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    p = _execute_chat_pipeline(req)

    def generate():
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
                gemini_text, esc_status, esc_latency = GeminiEscalationEngine.escalate_to_gemini(
                    user_query=p.user_input,
                    timeout=15.0
                )
                if gemini_text and len(gemini_text.strip()) > 10:
                    final_response = gemini_text.strip()
                else:
                    final_response = "I'm sorry, but I wasn't able to retrieve verified current information to answer your question right now."
                
                yield final_response
                awareness_dict = p.decision.awareness.dict() if p.decision.awareness else None
                update_memory(p.memory, p.user_input, final_response, awareness_dict=awareness_dict)
                append_message_to_conversation(p.conv_id, p.user_input, final_response, p.attachments)
                return

        full_response = ""
        prefix_buffer = ""
        prefix_checked = False

        for chunk in stream_model(
            p.prompt,
            model=p.selected_model,
            keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
            images=p.image_paths if p.image_paths else None
        ):
            full_response += chunk

            if not prefix_checked:
                prefix_buffer += chunk
                if len(prefix_buffer) > 20 or "\n" in prefix_buffer or " " in prefix_buffer:
                    cleaned_buffer = re.sub(r"^(?:saki|assistant|ai|\[saki\]|\[assistant\])\s*[-:ï¼š]?\s*", "", prefix_buffer, flags=re.IGNORECASE)
                    prefix_checked = True
                    if cleaned_buffer:
                        yield cleaned_buffer
            else:
                yield chunk

        if not prefix_checked and prefix_buffer:
            cleaned_buffer = re.sub(r"^(?:saki|assistant|ai|\[saki\]|\[assistant\])\s*[-:ï¼š]?\s*", "", prefix_buffer, flags=re.IGNORECASE)
            if cleaned_buffer:
                yield cleaned_buffer

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

        awareness_dict = p.decision.awareness.dict() if p.decision.awareness else None
        update_memory(p.memory, p.user_input, cleaned_response, awareness_dict=awareness_dict)
        append_message_to_conversation(p.conv_id, p.user_input, cleaned_response, p.attachments)

    return StreamingResponse(generate(), media_type="text/plain")




@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    p = _execute_chat_pipeline(req)

    response = call_model(
        p.prompt,
        model=p.selected_model,
        keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
        images=p.image_paths if p.image_paths else None
    )

    eval_result = evaluate_response(
        response,
        plan=p.plan,
        mode=p.decision.conversation_mode,
        evidence_items=p.evidence_items,
        evidence_package=p.evidence_package,
        action_decision=p.decision.action_decision if p.decision else None,
        user_query=p.user_input
    )
    final_response = eval_result.repaired_text

    # Last-Resort Gemini Answer Escalation (Sprint Final + Current Fact Fix)
    from backend.services.gemini_escalation import GeminiEscalationEngine
    already_attempted = getattr(req, "gemini_final_escalation_attempted", False)
    should_esc, esc_reason = GeminiEscalationEngine.should_escalate(
        user_query=p.user_input,
        final_response=final_response,
        eval_result=eval_result,
        evidence_package=p.evidence_package,
        action_decision=p.decision.action_decision if p.decision else None,
        already_attempted=already_attempted,
        evidence_items=p.evidence_items
    )

    final_response_source = "SAKI"
    if should_esc:
        gemini_text, esc_status, esc_latency = GeminiEscalationEngine.escalate_to_gemini(
            user_query=p.user_input,
            timeout=15.0
        )
        if gemini_text and len(gemini_text.strip()) > 10:
            final_response = gemini_text.strip()
            final_response_source = "GEMINI_FINAL_ESCALATION"
        else:
            final_response = "I'm sorry, but I wasn't able to retrieve verified current information to answer your question right now."
            final_response_source = "CONTROLLED_FAILURE"

    # Memory Admission Evaluation (BEFORE persisting, so decision can influence storage)
    from backend.services.memory_admission import MemoryAdmissionEngine, MemoryCandidate, SOURCE_USER, TYPE_PERSONAL_MEMORY

    # Determine if this interaction was web-derived
    _web_actions = {"WEB_SEARCH", "WEB_RESEARCH", "WEB_FETCH"}
    _action = p.decision.action_decision if p.decision else None
    _is_web_derived = _action and _action.action in _web_actions
    _user_wants_memory = any(kw in p.user_input.lower() for kw in ["remember", "prefer", "like", "building"])

    if _is_web_derived and not _user_wants_memory:
        # Block web-derived facts from entering long-term memory (Section 7: Memory Admission Control)
        adm_decision = None
    else:
        adm_candidate = MemoryCandidate(
            content=p.user_input,
            memory_type=TYPE_PERSONAL_MEMORY if _user_wants_memory else "WEB_EVIDENCE",
            source_type=SOURCE_USER if _user_wants_memory else "WEB"
        )
        adm_decision = MemoryAdmissionEngine.evaluate_candidate(adm_candidate)

    # Persist memory, awareness, and conversation history
    awareness_dict = p.decision.awareness.dict() if p.decision.awareness else None
    if not (_is_web_derived and not _user_wants_memory):
        update_memory(p.memory, p.user_input, final_response, awareness_dict=awareness_dict)
    append_message_to_conversation(p.conv_id, p.user_input, final_response, p.attachments)

    # Alias pipeline results for readability
    decision = p.decision
    evidence_items = p.evidence_items or []
    evidence_package = p.evidence_package
    research_result_obj = p.research_result_obj
    browser_obs_obj = p.browser_obs_obj
    computer_obs_obj = p.computer_obs_obj
    dev_task_obj = p.dev_task_obj
    git_telemetry_obj = p.git_telemetry_obj
    persistent_task_obj = p.persistent_task_obj
    active_ctx_items = p.active_ctx_items or []
    attn_mode = p.attn_mode
    unified_rag_pkg = p.unified_rag_pkg
    fused_knowledge_pkg = p.fused_knowledge_pkg
    knowledge_graph_pkg = p.knowledge_graph_pkg
    web_intel_res = p.web_intel_res
    adaptive_intel_res = p.adaptive_intel_res
    wf_telemetry = p.wf_telemetry

    return ChatResponse(
        response=final_response,
        intent=decision.task_type,
        mode=decision.conversation_mode,
        routing=decision.dict(),
        awareness=decision.awareness.dict() if decision.awareness else None,
        plan=ResponsePlanSchema(
            goal=p.plan.goal,
            tone=p.plan.tone,
            depth=p.plan.depth,
            acknowledge_emotion=p.plan.acknowledge_emotion,
            use_humor=p.plan.use_humor,
            ask_question=p.plan.ask_question,
            technical_detail=p.plan.technical_detail
        ),
        evaluation=EvaluationResultSchema(
            passed=eval_result.passed,
            score=eval_result.score,
            persona_issues=eval_result.persona_issues
        ),
        action_decision=decision.action_decision.dict() if decision.action_decision else None,
        world_access_evidence=[EvidenceItemSchema(**e.dict()) for e in evidence_items] if evidence_items else None,
        evidence_package=EvidencePackageSchema(**evidence_package.dict()) if evidence_package else None,
        research_result=ResearchResultSchema(**research_result_obj.dict()) if research_result_obj else None,
        memory_admission=adm_decision.dict() if adm_decision and hasattr(adm_decision, "dict") else None,

        browser_observation=BrowserObservationSchema(
            url=browser_obs_obj.url,
            title=browser_obs_obj.title,
            dom_snippet=browser_obs_obj.dom_snippet,
            interactive_elements=[e.dict() for e in browser_obs_obj.interactive_elements],
            text_content=browser_obs_obj.text_content[:500],
            retrieved_at=browser_obs_obj.retrieved_at,
            permission_status=browser_obs_obj.permission_status
        ) if browser_obs_obj else None,
        computer_observation=ComputerObservationSchema(
            action_type=computer_obs_obj.action_type,
            target_path=computer_obs_obj.target_path,
            content_snippet=computer_obs_obj.content_snippet,
            file_count=computer_obs_obj.file_count,
            risk_level=computer_obs_obj.risk_level,
            retrieved_at=computer_obs_obj.retrieved_at
        ) if computer_obs_obj else None,
        development_task=DevelopmentTaskSchema(
            task_id=dev_task_obj.task_id,
            user_request=dev_task_obj.user_request,
            objective=dev_task_obj.objective,
            status=dev_task_obj.status,
            files_changed=dev_task_obj.files_changed,
            tests_run=dev_task_obj.tests_run,
            tests_passed=dev_task_obj.tests_passed,
            summary=dev_task_obj.summary
        ) if dev_task_obj else None,
        git_github_telemetry=GitGitHubTelemetrySchema(
            operation=git_telemetry_obj.operation,
            repository=git_telemetry_obj.repository,
            branch=git_telemetry_obj.branch,
            status_state=git_telemetry_obj.status_state,
            details=git_telemetry_obj.details
        ) if git_telemetry_obj else None,
        persistent_task=SakiTaskSchema(
            task_id=persistent_task_obj.task_id,
            objective=persistent_task_obj.objective,
            status=persistent_task_obj.status,
            schedule_type=persistent_task_obj.schedule_type,
            trigger_condition=persistent_task_obj.trigger_condition,
            capability_scope=persistent_task_obj.capability_scope,
            created_at=persistent_task_obj.created_at,
            expires_at=persistent_task_obj.expires_at,
            retry_count=persistent_task_obj.retry_count,
            max_retries=persistent_task_obj.max_retries
        ) if persistent_task_obj else None,
        personal_context=PersonalContextTelemetrySchema(
            active_items_count=len(active_ctx_items),
            top_categories=list({i.category for i in active_ctx_items}),
            proactive_attention_mode=attn_mode
        ) if active_ctx_items else None,
        unified_knowledge=UnifiedKnowledgePackageSchema(
            total_candidates=unified_rag_pkg.total_candidates,
            sources_queried=unified_rag_pkg.sources_queried,
            has_conflicts=unified_rag_pkg.has_conflicts,
            candidates=[
                KnowledgeCandidateSchema(
                    id=c.id,
                    source_type=c.source_type,
                    content=c.content,
                    location=c.location,
                    confidence=c.confidence,
                    freshness=c.freshness,
                    relevance_score=c.relevance_score,
                    provenance_label=c.provenance_label
                ) for c in unified_rag_pkg.candidates
            ],
            details=unified_rag_pkg.details
        ) if unified_rag_pkg else None,
        knowledge_fusion=FusedKnowledgePackageSchema(
            total_claims=fused_knowledge_pkg.total_claims,
            supported_claims_count=fused_knowledge_pkg.supported_claims_count,
            has_conflicts=fused_knowledge_pkg.has_conflicts,
            claims=[
                FusedClaimSchema(
                    claim_id=c.claim_id,
                    subject=c.subject,
                    predicate=c.predicate,
                    object_value=c.object_value,
                    support_state=c.support_state,
                    confidence=c.confidence,
                    sources=c.sources
                ) for c in fused_knowledge_pkg.claims
            ],
            conflicts=[
                SourceConflictSchema(
                    conflict_id=conf.conflict_id,
                    claim_a=conf.claim_a,
                    source_a=conf.source_a,
                    claim_b=conf.claim_b,
                    source_b=conf.source_b,
                    resolution_status=conf.resolution_status
                ) for conf in fused_knowledge_pkg.conflicts
            ],
            details=fused_knowledge_pkg.details
        ) if fused_knowledge_pkg else None,
        knowledge_graph=KnowledgeGraphPackageSchema(
            total_nodes=knowledge_graph_pkg.total_nodes,
            total_edges=knowledge_graph_pkg.total_edges,
            nodes=[
                KnowledgeNodeSchema(
                    node_id=n.node_id,
                    node_type=n.node_type,
                    canonical_id=n.canonical_id,
                    label=n.label,
                    source=n.source,
                    confidence=n.confidence,
                    status=n.status
                ) for n in knowledge_graph_pkg.nodes
            ],
            edges=[
                KnowledgeEdgeSchema(
                    edge_id=e.edge_id,
                    source_node=e.source_node,
                    relation=e.relation,
                    target_node=e.target_node,
                    confidence=e.confidence,
                    status=e.status
                ) for e in knowledge_graph_pkg.edges
            ],
            details=knowledge_graph_pkg.details
        ) if knowledge_graph_pkg else None,
        web_intelligence=WebIntelligenceTelemetrySchema(
            queries_executed=web_intel_res.queries_executed,
            primary_sources_found=web_intel_res.primary_sources_found,
            browser_fallback_used=web_intel_res.browser_fallback_used,
            freshness_status=web_intel_res.freshness_status,
            details=web_intel_res.details
        ) if web_intel_res else None,
        adaptive_intelligence=AdaptiveIntelligenceTelemetrySchema(
            feedback_type=adaptive_intel_res.feedback_type,
            admitted_preferences=[
                PreferenceSchema(
                    preference_id=p_item.preference_id,
                    category=p_item.category,
                    value=p_item.value,
                    source=p_item.source,
                    confidence=p_item.confidence,
                    scope=p_item.scope,
                    status=p_item.status
                ) for p_item in adaptive_intel_res.admitted_preferences
            ],
            active_candidates=[
                LearningCandidateSchema(
                    candidate_id=c.candidate_id,
                    category=c.category,
                    proposed_change=c.proposed_change,
                    source=c.source,
                    confidence=c.confidence,
                    status=c.status
                ) for c in adaptive_intel_res.active_candidates
            ],
            details=adaptive_intel_res.details
        ) if adaptive_intel_res else None,
        autonomous_workflow=WorkflowTelemetrySchema(
            active_workflow=SakiWorkflowSchema(
                workflow_id=wf_telemetry.active_workflow.workflow_id,
                objective=wf_telemetry.active_workflow.objective,
                status=wf_telemetry.active_workflow.status,
                current_step_index=wf_telemetry.active_workflow.current_step_index,
                total_steps=len(wf_telemetry.active_workflow.steps),
                steps=[
                    WorkflowStepSchema(
                        step_id=st.step_id,
                        objective=st.objective,
                        capability=st.capability,
                        status=st.status
                    ) for st in wf_telemetry.active_workflow.steps
                ]
            ) if wf_telemetry and wf_telemetry.active_workflow else None,
            execution_status=wf_telemetry.execution_status if wf_telemetry else "IDLE",
            details=wf_telemetry.details if wf_telemetry else "No active workflow."
        ) if wf_telemetry else None
    )






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
    upload_dir = os.path.abspath(os.path.join(os.getcwd(), "data", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    return {
        "name": file.filename,
        "path": file_path,
        "size": len(content)
    }
