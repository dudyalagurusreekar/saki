import re
import json
from typing import List, Dict, Any
from brain.schemas import TaskPlan
from backend.services.ai_service import call_model

# Standard execution plan templates based on intent and complexity
PLAN_TEMPLATES: Dict[str, List[str]] = {
    "Coding": ["read_code", "analyze_requirements", "write_code", "verify", "answer"],
    "Debugging": ["read_code", "diagnose_error", "fix_code", "verify", "answer"],
    "Research": ["search", "read", "compare", "answer"],
    "News": ["search_news", "read_articles", "synthesize", "answer"],
    "Current Events": ["search", "read", "synthesize", "answer"],
    "Memory": ["fetch_memory", "integrate_context", "answer"],
    "Project": ["scan_workspace", "read_files", "analyze_structure", "answer"],
    "Learning": ["explain_concepts", "provide_examples", "answer"],
    "Planning": ["gather_goals", "generate_roadmap", "format_tasks", "answer"],
    "Math": ["parse_variables", "execute_calculation", "format_output", "answer"],
    "Casual Chat": ["generate_response"],
    "Writing": ["draft_content", "polish_text", "answer"],
    "Translation": ["detect_source", "translate_text", "verify_meaning", "answer"],
    "Vision": ["parse_image", "extract_features", "answer"],
    "Image Generation": ["expand_prompt", "trigger_generation", "answer"]
}

def generate_plan(
    query: str, 
    intent: str, 
    complexity: str, 
    skip_llm: bool = True
) -> TaskPlan:
    """
    Generates an execution plan (list of steps) for a request.
    Uses predefined templates or calls LLM for complex tasks.
    """
    # 1. Custom LLM planner for complex research or long running tasks
    if not skip_llm and complexity in ["Research", "Long Running"]:
        prompt = f"""
Given the following user query, generate a sequence of 3 to 6 short, lowercase, executable step names 
to fulfill it. E.g., for 'Compare Qwen3 and Llama 4': ["search", "read", "compare", "answer"].

Query: "{query}"
Intent: {intent}
Complexity: {complexity}

Respond ONLY with a JSON object in this format:
{{
  "steps": ["step1", "step2", "step3"]
}}
"""
        try:
            response = call_model(prompt)
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                steps = data.get("steps", [])
                if steps and isinstance(steps, list):
                    return TaskPlan(steps=[str(s).lower() for s in steps])
        except Exception:
            pass
            
    # 2. Template matching
    steps = PLAN_TEMPLATES.get(intent)
    if not steps:
        # Generic plan fallback
        if complexity == "Simple":
            steps = ["generate_response"]
        else:
            steps = ["parse_input", "process", "answer"]
            
    # Modify standard template if query contains URLs (add reading step)
    if "http" in query.lower() and "read" not in "".join(steps):
        steps = ["read_urls"] + steps
        
    return TaskPlan(steps=steps)
