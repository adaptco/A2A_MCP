"""
Vector ingestion engine module.
"""
import os
import json
import logging
from typing import List
from workers.embed_worker import EmbedWorker

logger = logging.getLogger("VectorIngestionEngine")

class VectorIngestionEngine:
    """
    Data-Plane Ingestion Engine.
    Handles repository snapshots by dispatching to EmbedWorker.
    """

    def __init__(self, output_dir: str = "pipeline/ledger/embeddings"):
        self.output_dir = output_dir
        # Dispatcher for embedding
        self.worker = EmbedWorker(output_dir=output_dir)

    async def process_snapshot(self, snapshot: dict, claims: dict) -> List[dict]:
        """
        Processes a full repository snapshot into canonical embeddings.
        Input: snapshot (JSON), claims (Auth Context)
        Output: List of vector nodes.
        """
        # 1. Flatten snapshot into nodes/spans
        # (Assuming snapshots have 'files' containing 'content')
        nodes = []
        for file in snapshot.get("files", []):
            nodes.append({
                "text": file.get("content", ""),
                "metadata": {
                    "source": file.get("path", "file_node"),
                    "provenance": claims.get("repository", "unknown")
                }
            })

        # 2. Dispatch to deterministic EmbedWorker (Batch Process)
        if not nodes:
            return []

        receipt = self.worker.embed_batch(nodes)

        # 3. Format result for knowledge store
        # (Each node gets its embedding and batch metadata)
        vector_nodes = []
        for res_node, raw_node in zip(receipt["results"], nodes):
            vector_nodes.append({
                "id": res_node["node_id"],
                "text": raw_node["text"],
                "embedding": res_node["embedding"],
                "batch_hash": receipt["batch_hash"],
                "model_version": receipt["model_version"],
                "provenance": raw_node["metadata"]["source"]
            })

        return vector_nodes

async def upsert_to_knowledge_store(nodes: List[dict]) -> dict:
    """
    Persistence Layer (Mocked).
    In a production system, this would write to ChromaDB/Pinecone.
    """
    # For now, we use a file-based JSON store for stable sharding
    logger.info("Upserting %s nodes to knowledge store.", len(nodes))
    store_dir = "pipeline/ledger/knowledge_store"
    os.makedirs(store_dir, exist_ok=True)

    for node in nodes:
        node_id = node["id"]
        with open(os.path.join(store_dir, f"{node_id}.json"), 'w', encoding='utf-8') as f:
            json.dump(node, f, indent=4)

    return {"status": "success", "count": len(nodes)}
