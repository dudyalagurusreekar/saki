# Saki AI — Personal + Project Knowledge Graph Specification
**Sprint 15 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Personal + Project Knowledge Graph Subsystem  

---

## 1. ARCHITECTURAL LAW & SUBSYSTEM OVERVIEW

Saki is **ONE integrated AI system**. The Knowledge Graph Engine ([`KnowledgeGraphEngine`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_graph.py#L75)) is a relationship indexing layer—**NOT a secondary graph agent (`GraphAgent`, `KnowledgeGraphAgent`, `GraphBrain`), second memory system, or separate vector database**.

The graph connects information already available across Saki (Goals, Projects, Tasks, Memories, Code Files, Repositories, GitHub state, and Decisions) to enhance context selection for Saki's central brain.

```
Existing Sources (S6 Memory, S9 Dev, S10 GitHub, S11 Tasks, S12 Personal Context)
      ↓
S13 Unified Knowledge Retrieval
      ↓
S14 Evidence & Knowledge Fusion
      ↓
Knowledge Graph Engine (backend/services/knowledge_graph.py)
    ├── 1. KnowledgeNode (USER, GOAL, PROJECT, TASK, MEMORY, REPOSITORY, FILE, PR)
    ├── 2. KnowledgeEdge (HAS_GOAL, HAS_TASK, AFFECTS, MODIFIES, RELATES_TO)
    ├── 3. Entity Resolution & Canonical Identity ("Saki AI" -> project:saki)
    ├── 4. Bounded Traversal Guard (MAX_DEPTH = 2, MAX_NODES = 20)
    ├── 5. Temporal Graph State (ACTIVE, SUPERSEDED, EXPIRED, REVOKED)
    └── 6. Memory Revocation Sync (Deleted memories invalidates graph edges)
      ↓
Privacy Policy Engine (Sprint 2 Outbound Boundary)
      ↓
Ranked Graph Context Package (ChatResponse.knowledge_graph)
      ↓
Saki Central Brain (Reasoning & Grounded Response Generation)
```

---

## 2. BOUNDED TRAVERSAL & ENTITY RESOLUTION

- **Traversal Limits**: To prevent exponential traversal latency, graph exploration is strictly bounded:
  - `MAX_GRAPH_NODES`: 20 nodes max per response package
  - `MAX_GRAPH_EDGES`: 30 edges max per response package
  - `MAX_GRAPH_DEPTH`: 2 hops max from active context anchor
- **Entity Canonical Resolution**: [`KnowledgeGraphEngine.resolve_entity_canonical()`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_graph.py#L82) maps entity variations (e.g. `"Saki"`, `"Saki AI"`) to canonical ID `project:saki`.

---

## 3. MEMORY REVOCATION SYNC & ACCESS ISOLATION

- **Memory Revocation Sync**: [`KnowledgeGraphEngine.sync_memory_revocation()`](file:///c:/Users/gurus/work/saki/backend/services/knowledge_graph.py#L130) automatically transitions graph nodes and incident edges to `STATUS_REVOKED` when underlying user memory or context items are revoked or deleted.
- **Cross-User Access Control**: Every graph node and edge carries `access_scope = PRIVATE` preventing cross-user graph leaks.
