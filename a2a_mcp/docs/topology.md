## MoA ↔ MoE Routing Topology

**Control plane (core-orchestrator)**
- Registry: `registry/agents/agent_registry.json` binds agents to manifests, prompt contracts, owner roles, capability sets, tool allowlists, and execution environment constraints.
- Routing policy: `registry/routing/routing_policy.v1.json` deterministically selects experts by intent.
- Expert catalog: `registry/experts/expert_catalog.v1.json` lists capabilities.

**Knowledge plane (SSOT)**
- Chunk set: digital threads stored as JSONL.
- Vector store: Postgres + pgvector holds embeddings.
- Manifest: describes embedding model, retrieval policy, and index metadata.

**Runtime flow**
`registry → routing policy → manifest → vector store → experts`

The MoA runtime loads the registry, selects the agent by project/vertical, loads the manifest, retrieves context from pgvector, chooses experts via routing policy, and assembles a prompt that cites retrieved `thread_id` values before handing off to downstream experts.
