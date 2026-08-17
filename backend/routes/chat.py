import os
import json
import re
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse
from backend.models.schemas import ChatRequest, ChatResponse, ResponsePlanSchema, EvaluationResultSchema
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


def _load_conversations_data() -> Dict[str, Any]:
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
            {"role": "assistant", "content": "Hey! Good to see you. What are we building or exploring today? 🌸"}
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
            {"role": "assistant", "content": "Hey! Good to see you. What are we building or exploring today? 🌸"}
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
# STREAMING AND STANDARD CHAT
# -------------------------
@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    user_input = req.message.strip()
    conv_id = req.conversation_id or "default-session"
    attachment_context = get_attachment_context(req)
    prompt_input = user_input + attachment_context

    memory = load_memory()
    history_context = format_history_context(memory.get("conversation_history", []))

    # Check for user correction (Learning Loop)
    correction = detect_user_correction(user_input)
    if correction:
        from backend.services.memory_service import _upsert_memory
        _upsert_memory(memory, correction)

    prev_awareness_raw = memory.get("awareness")
    prev_awareness = SakiAwareness(**prev_awareness_raw) if prev_awareness_raw else None

    # Model Orchestration
    decision = SakiModelOrchestrator.classify_request(
        query=user_input,
        attachments=req.attachments,
        previous_awareness=prev_awareness,
        memory_data=memory
    )

    # World Access, Research & Browser Automation Subsystem
    evidence_items = []
    evidence_prompt_block = ""
    evidence_package = None
    research_result_obj = None
    browser_obs_obj = None
    if decision.action_decision and decision.action_decision.requires_world_access:
        from backend.services.world_access_manager import WorldAccessManager
        if decision.action_decision.action in ["BROWSER_READ", "BROWSER_INTERACT"]:
            from backend.services.browser_controller import BrowserController, BrowserAction
            url_match = re.search(r"https?://[^\s]+", user_input)
            target_url = url_match.group(0) if url_match else "https://duckduckgo.com"
            b_action = BrowserAction(action_type=decision.action_decision.action, url=target_url)
            browser_obs_obj = BrowserController.execute_action(b_action)
            evidence_prompt_block = browser_obs_obj.grounded_prompt_block
        elif decision.action_decision.action == "WEB_RESEARCH":
            from backend.services.research_planner import ResearchPlanner
            research_result_obj = ResearchPlanner.execute_research(user_input)
            evidence_package = research_result_obj.evidence_package
            evidence_items = evidence_package.evidence_items if evidence_package else []
            evidence_prompt_block = research_result_obj.grounded_prompt_block
        else:
            evidence_items, evidence_prompt_block, evidence_package = WorldAccessManager.execute_action_package(
                decision.action_decision,
                user_input,
                req.attachments
            )
    # Computer Subsystem Execution
    computer_obs_obj = None
    if decision.action_decision and decision.action_decision.action == "CODING":
        from backend.services.computer_controller import ComputerController, ComputerAction
        c_action = ComputerAction(action_type="INSPECT_WORKSPACE", target_path=r"c:\Users\gurus\work\saki")
        computer_obs_obj = ComputerController.execute_action(c_action)

    user_prefs = [m["content"] for m in memory.get("memories", []) if m.get("type") == "PREFERENCE"]
    plan = plan_response(decision.cognitive_state, user_input, user_preferences=user_prefs)

    memory_context = build_smart_memory_context(
        memory=memory,
        query=user_input,
        limit=settings.MEMORY_CONTEXT_LIMIT,
        active_mode=decision.conversation_mode,
        active_project=decision.awareness.current_project if decision.awareness else None
    )

    prompt = build_orchestrated_prompt(decision, plan, prompt_input, memory_context, history_context)
    selected_model = decision.selected_model

    # Image attachments for Gemma 3
    image_paths = []
    if req.attachments:
        for att in req.attachments:
            if att.get("path") and (
                att.get("type") == "image" 
                or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            ):
                image_paths.append(att["path"])

    def generate():
        full_response = ""
        prefix_buffer = ""
        prefix_checked = False

        for chunk in stream_model(
            prompt, 
            model=selected_model, 
            keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
            images=image_paths if image_paths else None
        ):
            full_response += chunk
            
            # Initial speaker prefix filter (buffer first ~15 chars to strip Saki:, Assistant:, etc.)
            if not prefix_checked:
                prefix_buffer += chunk
                if len(prefix_buffer) > 20 or "\n" in prefix_buffer or " " in prefix_buffer:
                    cleaned_buffer = re.sub(r"^(?:saki|assistant|ai|\[saki\]|\[assistant\])\s*[-:：]?\s*", "", prefix_buffer, flags=re.IGNORECASE)
                    prefix_checked = True
                    if cleaned_buffer:
                        yield cleaned_buffer
            else:
                yield chunk

        if not prefix_checked and prefix_buffer:
            cleaned_buffer = re.sub(r"^(?:saki|assistant|ai|\[saki\]|\[assistant\])\s*[-:：]?\s*", "", prefix_buffer, flags=re.IGNORECASE)
            if cleaned_buffer:
                yield cleaned_buffer

        # Fallback search if helpless
        if is_helpless_response(full_response):
            results = safe_search(user_input)
            if results:
                follow_prompt = f"Answer naturally as Saki using these search results:\n{results}\nQuery: {user_input}\nSaki:"
                for chunk in stream_model(follow_prompt, model=settings.MODEL_QWEN3, keep_alive=settings.MODEL_KEEP_ALIVE_SESSION):
                    full_response += chunk
                    yield chunk

        # Post-evaluation and cleansing
        eval_result = evaluate_response(full_response, plan=plan, mode=decision.conversation_mode)
        cleaned_response = eval_result.repaired_text
        
        # Persist memory, awareness, and conversation history
        awareness_dict = decision.awareness.dict() if decision.awareness else None
        update_memory(memory, user_input, cleaned_response, awareness_dict=awareness_dict)
        append_message_to_conversation(conv_id, user_input, cleaned_response, req.attachments)

    return StreamingResponse(generate(), media_type="text/plain")


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_input = req.message.strip()
    conv_id = req.conversation_id or "default-session"
    attachment_context = get_attachment_context(req)
    prompt_input = user_input + attachment_context

    memory = load_memory()
    history_context = format_history_context(memory.get("conversation_history", []))

    correction = detect_user_correction(user_input)
    if correction:
        from backend.services.memory_service import _upsert_memory
        _upsert_memory(memory, correction)

    prev_awareness_raw = memory.get("awareness")
    prev_awareness = SakiAwareness(**prev_awareness_raw) if prev_awareness_raw else None

    decision = SakiModelOrchestrator.classify_request(
        query=user_input,
        attachments=req.attachments,
        previous_awareness=prev_awareness,
        memory_data=memory
    )

    # World Access, Research & Browser Automation Subsystem
    evidence_items = []
    evidence_prompt_block = ""
    evidence_package = None
    research_result_obj = None
    browser_obs_obj = None
    if decision.action_decision and decision.action_decision.requires_world_access:
        from backend.services.world_access_manager import WorldAccessManager
        if decision.action_decision.action in ["BROWSER_READ", "BROWSER_INTERACT"]:
            from backend.services.browser_controller import BrowserController, BrowserAction
            url_match = re.search(r"https?://[^\s]+", user_input)
            target_url = url_match.group(0) if url_match else "https://duckduckgo.com"
            b_action = BrowserAction(action_type=decision.action_decision.action, url=target_url)
            browser_obs_obj = BrowserController.execute_action(b_action)
            evidence_prompt_block = browser_obs_obj.grounded_prompt_block
        elif decision.action_decision.action == "WEB_RESEARCH":
            from backend.services.research_planner import ResearchPlanner
            research_result_obj = ResearchPlanner.execute_research(user_input)
            evidence_package = research_result_obj.evidence_package
            evidence_items = evidence_package.evidence_items if evidence_package else []
            evidence_prompt_block = research_result_obj.grounded_prompt_block
        else:
            evidence_items, evidence_prompt_block, evidence_package = WorldAccessManager.execute_action_package(
                decision.action_decision,
                user_input,
                req.attachments
            )
        if evidence_prompt_block:
            prompt_input = prompt_input + evidence_prompt_block

    # Computer Subsystem Execution
    computer_obs_obj = None
    if decision.action_decision and decision.action_decision.action == "CODING":
        from backend.services.computer_controller import ComputerController, ComputerAction
        c_action = ComputerAction(action_type="INSPECT_WORKSPACE", target_path=r"c:\Users\gurus\work\saki")
        computer_obs_obj = ComputerController.execute_action(c_action)

    user_prefs = [m["content"] for m in memory.get("memories", []) if m.get("type") == "PREFERENCE"]

    plan = plan_response(decision.cognitive_state, user_input, user_preferences=user_prefs)

    memory_context = build_smart_memory_context(
        memory=memory,
        query=user_input,
        limit=settings.MEMORY_CONTEXT_LIMIT,
        active_mode=decision.conversation_mode,
        active_project=decision.awareness.current_project if decision.awareness else None
    )

    prompt = build_orchestrated_prompt(decision, plan, prompt_input, memory_context, history_context)
    selected_model = decision.selected_model

    image_paths = []
    if req.attachments:
        for att in req.attachments:
            if att.get("path") and (
                att.get("type") == "image" 
                or str(att.get("name", "")).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            ):
                image_paths.append(att["path"])

    response = call_model(
        prompt, 
        model=selected_model, 
        keep_alive=settings.MODEL_KEEP_ALIVE_SESSION,
        images=image_paths if image_paths else None
    )

    if is_helpless_response(response):
        results = safe_search(user_input)
        if results:
            response = call_model(
                f"Answer naturally as Saki using these search results:\n{results}\nQuery: {user_input}\nSaki:",
                model=settings.MODEL_QWEN3
            )

    eval_result = evaluate_response(response, plan=plan, mode=decision.conversation_mode)
    final_response = eval_result.repaired_text

    awareness_dict = decision.awareness.dict() if decision.awareness else None
    update_memory(memory, user_input, final_response, awareness_dict=awareness_dict)
    append_message_to_conversation(conv_id, user_input, final_response, req.attachments)

    # Memory Admission Evaluation
    from backend.services.memory_admission import MemoryAdmissionEngine, MemoryCandidate, SOURCE_USER, TYPE_PERSONAL_MEMORY
    adm_candidate = MemoryCandidate(
        content=user_input,
        memory_type=TYPE_PERSONAL_MEMORY if any(p in user_input.lower() for p in ["remember", "prefer", "like", "building"]) else "WEB_EVIDENCE",
        source_type=SOURCE_USER if any(p in user_input.lower() for p in ["remember", "prefer", "like", "building"]) else "WEB"
    )
    adm_decision = MemoryAdmissionEngine.evaluate_candidate(adm_candidate)

    return ChatResponse(
        response=final_response,
        intent=decision.task_type,
        mode=decision.conversation_mode,
        routing=decision.dict(),
        awareness=decision.awareness.dict() if decision.awareness else None,
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
        action_decision=decision.action_decision.dict() if decision.action_decision else None,
        world_access_evidence=[EvidenceItemSchema(**e.dict()) for e in evidence_items] if evidence_items else None,
        evidence_package=EvidencePackageSchema(**evidence_package.dict()) if evidence_package else None,
        research_result=ResearchResultSchema(**research_result_obj.dict()) if research_result_obj else None,
        memory_admission=MemoryAdmissionDecisionSchema(**adm_decision.dict()) if adm_decision else None,
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
        ) if computer_obs_obj else None
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
