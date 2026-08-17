"""
Saki Personal + Project Knowledge Graph Subsystem (KnowledgeGraphEngine)
Provides a lightweight, zero-dependency in-memory graph relationship layer connecting User context,
Goals, Projects, Tasks, Memories, Files, Repositories, GitHub PRs/Issues, and Decisions.
"""

import time
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from backend.core.privacy import PrivacyPolicyEngine, OutboundRequest, DECISION_BLOCK
from backend.services.knowledge_fusion import FusedKnowledgePackage, FusedClaim
from backend.services.personal_context import PersonalContextEngine, STATUS_ACTIVE, STATUS_REVOKED, STATUS_SUPERSEDED

# Node Types
NT_USER = "USER"
NT_GOAL = "GOAL"
NT_PROJECT = "PROJECT"
NT_TASK = "TASK"
NT_MEMORY = "MEMORY"
NT_DOCUMENT = "DOCUMENT"
NT_FILE = "FILE"
NT_CODE_SYMBOL = "CODE_SYMBOL"
NT_REPOSITORY = "REPOSITORY"
NT_COMMIT = "COMMIT"
NT_ISSUE = "ISSUE"
NT_PULL_REQUEST = "PULL_REQUEST"
NT_RESEARCH = "RESEARCH"
NT_SOURCE = "SOURCE"
NT_EVIDENCE = "EVIDENCE"
NT_DECISION = "DECISION"

# Relation Types
REL_OWNS = "OWNS"
REL_HAS_GOAL = "HAS_GOAL"
REL_CONTAINS = "CONTAINS"
REL_RELATES_TO = "RELATES_TO"
REL_USES = "USES"
REL_HAS_TASK = "HAS_TASK"
REL_AFFECTS = "AFFECTS"
REL_TRACKED_BY = "TRACKED_BY"
REL_MODIFIES = "MODIFIES"
REL_DESCRIBES = "DESCRIBES"
REL_SUPPORTS = "SUPPORTS"

# Statuses
STATUS_ACTIVE = "ACTIVE"
STATUS_SUPERSEDED = "SUPERSEDED"
STATUS_EXPIRED = "EXPIRED"
STATUS_REVOKED = "REVOKED"

# Traversal Limits
MAX_GRAPH_NODES = 20
MAX_GRAPH_EDGES = 30
MAX_GRAPH_DEPTH = 2


# -------------------------
# DATA MODELS
# -------------------------
class KnowledgeNode(BaseModel):
    node_id: str = Field(default_factory=lambda: f"node-{time.time_ns() % 1000000}")
    node_type: str = NT_PROJECT
    canonical_id: str = "project:saki"
    label: str
    source: str = "USER_EXPLICIT"
    provenance: str = "Saki Architecture Definition"
    confidence: float = 1.0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: str = STATUS_ACTIVE
    access_scope: str = "PRIVATE"


class KnowledgeEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: f"edge-{time.time_ns() % 1000000}")
    source_node: str
    relation: str = REL_RELATES_TO
    target_node: str
    provenance: str = "System Graph Extraction"
    confidence: float = 1.0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: str = STATUS_ACTIVE
    access_scope: str = "PRIVATE"


class KnowledgeGraphPackage(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    nodes: List[KnowledgeNode] = Field(default_factory=list)
    edges: List[KnowledgeEdge] = Field(default_factory=list)
    details: str = "Knowledge graph traversal completed successfully."


# -------------------------
# KNOWLEDGE GRAPH ENGINE
# -------------------------
class KnowledgeGraphEngine:
    """
    Lightweight in-memory Knowledge Graph indexing/relationship layer.
    """

    _nodes: Dict[str, KnowledgeNode] = {}
    _edges: List[KnowledgeEdge] = []

    @classmethod
    def resolve_entity_canonical(cls, label: str) -> str:
        """
        Resolves entity variations (e.g. 'Saki', 'Saki AI') to canonical IDs.
        """
        label_lower = label.lower().strip()
        if "saki" in label_lower:
            return "project:saki"
        if "browser" in label_lower:
            return "task:browser_integration"
        if "git" in label_lower or "github" in label_lower:
            return "repo:github_capability"
        return f"entity:{label_lower.replace(' ', '_')[:30]}"

    @classmethod
    def initialize_base_graph(cls):
        if not cls._nodes:
            user_node = KnowledgeNode(
                node_type=NT_USER,
                canonical_id="user:default",
                label="User",
                provenance="System User Session"
            )
            project_node = KnowledgeNode(
                node_type=NT_PROJECT,
                canonical_id="project:saki",
                label="Saki AI Project",
                provenance="Repository Architecture"
            )
            goal_node = KnowledgeNode(
                node_type=NT_GOAL,
                canonical_id="goal:complete_saki_architecture",
                label="Build Saki Integrated AI Architecture",
                provenance="User Explicit Goal"
            )
            
            cls._nodes[user_node.canonical_id] = user_node
            cls._nodes[project_node.canonical_id] = project_node
            cls._nodes[goal_node.canonical_id] = goal_node

            cls._edges.append(KnowledgeEdge(
                source_node=user_node.canonical_id,
                relation=REL_OWNS,
                target_node=project_node.canonical_id
            ))
            cls._edges.append(KnowledgeEdge(
                source_node=user_node.canonical_id,
                relation=REL_HAS_GOAL,
                target_node=goal_node.canonical_id
            ))
            cls._edges.append(KnowledgeEdge(
                source_node=goal_node.canonical_id,
                relation=REL_RELATES_TO,
                target_node=project_node.canonical_id
            ))

    @classmethod
    def sync_memory_revocation(cls, keyword: str):
        """
        Invalidates associated graph nodes and edges when memory/context is revoked.
        """
        kw_lower = keyword.lower()
        for node in cls._nodes.values():
            if kw_lower in node.label.lower() and node.status == STATUS_ACTIVE:
                node.status = STATUS_REVOKED
                node.updated_at = time.time()
        for edge in cls._edges:
            if edge.status == STATUS_ACTIVE:
                src_node = cls._nodes.get(edge.source_node)
                tgt_node = cls._nodes.get(edge.target_node)
                if (src_node and src_node.status == STATUS_REVOKED) or (tgt_node and tgt_node.status == STATUS_REVOKED):
                    edge.status = STATUS_REVOKED
                    edge.updated_at = time.time()

    @classmethod
    def traverse_subgraph(cls, query: str, fused_pkg: Optional[FusedKnowledgePackage] = None) -> KnowledgeGraphPackage:
        cls.initialize_base_graph()
        query_lower = query.lower()

        # Dynamic graph node expansion based on query context
        if "browser" in query_lower:
            browser_task = KnowledgeNode(
                node_type=NT_TASK,
                canonical_id="task:browser_integration",
                label="Browser Automation Subsystem",
                provenance="Sprint 7 Browser Controller"
            )
            cls._nodes[browser_task.canonical_id] = browser_task
            cls._edges.append(KnowledgeEdge(
                source_node="project:saki",
                relation=REL_HAS_TASK,
                target_node=browser_task.canonical_id
            ))

        # Filter active nodes matching query canonical identities or top-level project neighborhood
        active_nodes = [n for n in cls._nodes.values() if n.status == STATUS_ACTIVE][:MAX_GRAPH_NODES]
        active_node_ids = {n.canonical_id for n in active_nodes}
        
        active_edges = [e for e in cls._edges if e.status == STATUS_ACTIVE and e.source_node in active_node_ids and e.target_node in active_node_ids][:MAX_GRAPH_EDGES]

        return KnowledgeGraphPackage(
            total_nodes=len(active_nodes),
            total_edges=len(active_edges),
            nodes=active_nodes,
            edges=active_edges,
            details=f"Traversed {len(active_nodes)} active nodes and {len(active_edges)} edges."
        )
