## End-to-End Dataflow

1. Build knowledge plane (in SSOT):
   - Start vector store: `cd infra/vectorstore && docker compose up -d`
   - Threadify corpus: `python pipelines/threading/threadify.py --config ./threadify.config.json --out ./data/corpus/threads/qube_core/simulation/threads.jsonl`
   - Embed + upsert: `python pipelines/embedding/embed_upsert.py --pg-dsn "dbname=ragdb user=raguser password=ragpass host=localhost" --threads ./data/corpus/threads/qube_core/simulation/threads.jsonl`
   - Retrieval smoke test: `python pipelines/validation/retrieval_smoke_test.py --pg-dsn "dbname=ragdb user=raguser password=ragpass host=localhost" --query "key principles and decisions" --expect-min 3`
   - Build manifest: `python pipelines/manifests/build_manifest.py --project axq:project:qube_core --vertical axq:vertical:simulation --corpus axq:corpus:qube_core.simulation --chunk-set ./data/corpus/threads/qube_core/simulation/threads.jsonl`

2. Run MoA (in core-orchestrator):
   - `python -m packages.moa_runtime.cli --registry registry/agents/agent_registry.json --policy registry/routing/routing_policy.v1.json --manifest ../ssot/manifests/rag/qube_core/simulation/CURRENT.json --pg-dsn "dbname=ragdb user=raguser password=ragpass host=localhost" --project axq:project:qube_core --vertical axq:vertical:simulation --intent feature_build --query "Build the routing network plumbing"`

This deterministic path wires registry → manifest → vector store → experts and assembles a prompt that cites retrieved digital thread IDs.
