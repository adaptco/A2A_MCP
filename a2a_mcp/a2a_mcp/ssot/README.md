## SSOT Knowledge Plane Scaffolding

Run the deterministic pipeline locally:

```bash
# 1) Start vector store
(cd infra/vectorstore && docker compose up -d)

# 2) Create threads.jsonl from configured inputs
python pipelines/threading/threadify.py --config ./threadify.config.json --out ./data/corpus/threads/qube_core/simulation/threads.jsonl

# 3) Embed + upsert
python pipelines/embedding/embed_upsert.py --pg-dsn "dbname=ragdb user=raguser password=ragpass host=localhost" --threads ./data/corpus/threads/qube_core/simulation/threads.jsonl

# 4) Smoke test retrieval
python pipelines/validation/retrieval_smoke_test.py --pg-dsn "dbname=ragdb user=raguser password=ragpass host=localhost" --query "key principles and decisions" --expect-min 3

# 5) Build manifest (writes CURRENT.json)
python pipelines/manifests/build_manifest.py --project axq:project:qube_core --vertical axq:vertical:simulation --corpus axq:corpus:qube_core.simulation --chunk-set ./data/corpus/threads/qube_core/simulation/threads.jsonl
```

This sequence produces deterministic embeddings, loads them into pgvector, validates retrieval, and emits an index manifest consumable by the MoA runtime.
