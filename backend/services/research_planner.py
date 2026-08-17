"""
Saki Bounded Autonomous Web Research Subsystem — ResearchPlanner, ResearchBudget & ResearchResult
Orchestrates bounded multi-step web research loops, gap analysis, query diversification,
hard executable budget safeguards, and grounded citation synthesis.
"""

import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.evidence_engine import (
    EvidenceIntelligenceEngine,
    EvidencePackage,
    EvidenceItem,
    EVIDENCE_STATUS_SUFFICIENT,
    EVIDENCE_STATUS_INSUFFICIENT,
    EVIDENCE_STATUS_CONTRADICTORY,
    CONFLICT_DIRECT
)


# -------------------------
# CONSTANTS & CONSTANTS
# -------------------------
STEP_PLANNED = "PLANNED"
STEP_RUNNING = "RUNNING"
STEP_COMPLETED = "COMPLETED"
STEP_FAILED = "FAILED"
STEP_SKIPPED = "SKIPPED"

STOP_EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT"
STOP_BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
STOP_MAX_DEPTH_REACHED = "MAX_DEPTH_REACHED"
STOP_NO_NEW_INFORMATION = "NO_NEW_INFORMATION"
STOP_PRIVACY_BLOCKED = "PRIVACY_BLOCKED"
STOP_CONFLICT_UNRESOLVABLE = "CONFLICT_UNRESOLVABLE"


# -------------------------
# RESEARCH BUDGET & MODELS
# -------------------------
class ResearchBudget(BaseModel):
    max_searches: int = 3
    max_fetches: int = 2
    max_depth: int = 3
    max_runtime: float = 15.0
    max_total_results: int = 15
    max_total_bytes: int = 1000000


class ResearchStep(BaseModel):
    step_id: str = Field(default_factory=lambda: f"step-{time.time_ns() % 1000000}")
    query: str
    purpose: str = "Search for evidence"
    status: str = Field(default=STEP_PLANNED)
    result_count: int = 0
    evidence_count: int = 0
    timestamp: float = Field(default_factory=time.time)


class ResearchPlan(BaseModel):
    research_id: str = Field(default_factory=lambda: f"res-{time.time_ns() % 1000000}")
    original_question: str
    objective: str
    initial_queries: List[str] = Field(default_factory=list)
    budget: ResearchBudget = Field(default_factory=ResearchBudget)
    stop_conditions: List[str] = Field(default_factory=list)


class ResearchState(BaseModel):
    completed_steps: List[ResearchStep] = Field(default_factory=list)
    pending_steps: List[ResearchStep] = Field(default_factory=list)
    raw_results_collected: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_package: Optional[EvidencePackage] = None
    searches_count: int = 0
    fetches_count: int = 0
    depth_count: int = 0
    start_time: float = Field(default_factory=time.time)
    stop_reason: Optional[str] = None


class ResearchGap(BaseModel):
    description: str
    importance: str = "IMPORTANT"  # CRITICAL, IMPORTANT, OPTIONAL
    recommended_query: str


class ResearchMatrix(BaseModel):
    entities: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    coverage: Dict[str, Dict[str, bool]] = Field(default_factory=dict)


class ResearchResult(BaseModel):
    research_id: str
    question: str
    summary: str
    evidence_package: Optional[EvidencePackage] = None
    grounded_prompt_block: str = ""
    sources_consulted: int = 0
    searches_performed: int = 0
    conflicts_detected: int = 0
    limitations: List[str] = Field(default_factory=list)
    stop_reason: str = STOP_EVIDENCE_SUFFICIENT
    research_duration: float = 0.0


# -------------------------
# RESEARCH PLANNER ENGINE
# -------------------------
class ResearchPlanner:
    """
    Bounded Autonomous Web Research Planner.
    Formulates research plans, executes bounded multi-step search loops,
    evaluates information gaps, enforces hard budgets, and synthesizes grounded evidence.
    """

    @classmethod
    def create_plan(cls, question: str, depth_level: str = "STANDARD") -> ResearchPlan:
        # Determine budget based on user depth preference
        if depth_level == "QUICK":
            budget = ResearchBudget(max_searches=1, max_fetches=1, max_depth=1, max_runtime=5.0)
        elif depth_level == "DEEP":
            budget = ResearchBudget(max_searches=5, max_fetches=3, max_depth=4, max_runtime=25.0)
        else:  # STANDARD
            budget = ResearchBudget(max_searches=3, max_fetches=2, max_depth=3, max_runtime=15.0)

        # Formulate initial queries
        initial_query = question.strip()
        queries = [initial_query]

        # For comparison tasks, add dimension query
        if "compare" in question.lower() or "vs" in question.lower():
            queries.append(f"{initial_query} comparison benchmark features")

        return ResearchPlan(
            original_question=question,
            objective=f"Gather verified evidence to answer: '{question}'",
            initial_queries=queries,
            budget=budget,
            stop_conditions=[
                "Evidence sufficient to answer question",
                "Max searches/fetches reached",
                "No new information discovered",
                "Privacy policy blocked query"
            ]
        )

    @classmethod
    def execute_research(
        cls,
        question: str,
        depth_level: str = "STANDARD"
    ) -> ResearchResult:
        """
        Executes bounded autonomous web research loop safely in pure executable Python.
        """
        plan = cls.create_plan(question, depth_level=depth_level)
        state = ResearchState()
        
        from backend.services.world_access_manager import DuckDuckGoSearchProvider
        
        seen_queries = set()
        pending_queries = list(plan.initial_queries)
        
        # HARD BOUNDED PYTHON LOOP
        while pending_queries:
            now = time.time()
            
            # 1. HARD BUDGET & TIME CHECKS
            if state.searches_count >= plan.budget.max_searches:
                state.stop_reason = STOP_BUDGET_EXHAUSTED
                break
            if state.depth_count >= plan.budget.max_depth:
                state.stop_reason = STOP_MAX_DEPTH_REACHED
                break
            if (now - state.start_time) >= plan.budget.max_runtime:
                state.stop_reason = STOP_BUDGET_EXHAUSTED
                break

            current_query = pending_queries.pop(0)
            canon_q = current_query.strip().lower()
            if canon_q in seen_queries:
                continue
            seen_queries.add(canon_q)

            # 2. PRIVACY GATE EVALUATION
            outbound_req = OutboundRequest(
                action="WEB_RESEARCH",
                destination="PUBLIC_SEARCH",
                query=current_query,
                privacy_mode=settings.PRIVACY_MODE
            )
            privacy_decision = PrivacyPolicyEngine.evaluate_request(outbound_req)
            if privacy_decision.decision in [DECISION_BLOCK]:
                state.stop_reason = STOP_PRIVACY_BLOCKED
                break

            sanitized_q = privacy_decision.sanitized_request or current_query

            # 3. EXECUTE SEARCH STEP
            step = ResearchStep(query=sanitized_q, purpose=f"Step {state.searches_count+1} search")
            step.status = STEP_RUNNING
            state.searches_count += 1
            state.depth_count += 1

            raw_results = DuckDuckGoSearchProvider.search(sanitized_q, max_results=3)
            step.result_count = len(raw_results)
            step.status = STEP_COMPLETED if raw_results else STEP_FAILED

            prev_unique_count = len(state.raw_results_collected)
            state.raw_results_collected.extend(raw_results)
            state.completed_steps.append(step)

            # 4. EVIDENCE EVALUATION VIA EVIDENCE ENGINE
            state.evidence_package = EvidenceIntelligenceEngine.process_and_synthesize(
                query=question,
                raw_items=state.raw_results_collected
            )

            # Check if new information was added
            new_info_count = len(state.raw_results_collected) - prev_unique_count
            if new_info_count == 0 and state.searches_count > 1:
                state.stop_reason = STOP_NO_NEW_INFORMATION
                break

            # 5. CHECK STOPPING CONDITIONS & GAP ANALYSIS
            if state.evidence_package.evidence_status == EVIDENCE_STATUS_SUFFICIENT and len(state.evidence_package.sources) >= 2:
                state.stop_reason = STOP_EVIDENCE_SUFFICIENT
                break

            # 6. DIVERSIFY SEARCH IF CONFLICT OR GAP DISCOVERED
            if state.evidence_package.conflicts and state.searches_count < plan.budget.max_searches:
                conflict = state.evidence_package.conflicts[0]
                verification_query = f"{sanitized_q} official documentation verification"
                if verification_query.strip().lower() not in seen_queries:
                    pending_queries.append(verification_query)

        if not state.stop_reason:
            state.stop_reason = STOP_EVIDENCE_SUFFICIENT if state.raw_results_collected else STOP_NO_NEW_INFORMATION

        # 7. SYNTHESIZE FINAL RESEARCH RESULT
        duration = round(time.time() - state.start_time, 2)
        grounded_block = EvidenceIntelligenceEngine.format_grounded_prompt_block(state.evidence_package) if state.evidence_package else ""

        limitations = []
        if state.stop_reason == STOP_BUDGET_EXHAUSTED:
            limitations.append("Research halted due to maximum query budget limit.")
        elif state.stop_reason == STOP_PRIVACY_BLOCKED:
            limitations.append("Research query was restricted by local Privacy Boundary.")
        elif state.stop_reason == STOP_CONFLICT_UNRESOLVABLE:
            limitations.append("Retrieved web sources contain unresolved conflicts.")

        return ResearchResult(
            research_id=plan.research_id,
            question=question,
            summary=f"Autonomous research completed in {state.searches_count} step(s).",
            evidence_package=state.evidence_package,
            grounded_prompt_block=grounded_block,
            sources_consulted=len(state.evidence_package.sources) if state.evidence_package else 0,
            searches_performed=state.searches_count,
            conflicts_detected=len(state.evidence_package.conflicts) if state.evidence_package else 0,
            limitations=limitations,
            stop_reason=state.stop_reason,
            research_duration=duration
        )
