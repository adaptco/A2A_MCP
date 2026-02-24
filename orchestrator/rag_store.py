from __future__ import annotations

from typing import Any, Dict, List, Optional

from orchestrator.storage import DBManager
from schemas.hmlsl import HMLSLArtifact
from world_vectors.encoder import EmbeddingEncoder
from world_vectors.vault import VectorVault


class RAGVectorStore:
    """
    Persistent RAG Vector Store for HMLSL artifacts.
    Handles ingestion, hierarchical indexing, and semantic search.
    """

    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.encoder = EmbeddingEncoder()
        # In-memory store for now, backed by DB persistence of artifacts
        # In a real production scenario, this would interface with a dedicated
        # vector DB (e.g., Qdrant, PGVector)
        self.vector_index = VectorVault(encoder=self.encoder)
        self.hierarchy_index: Dict[str, Dict[str, List[str]]] = {}

    def ingest_hmlsl_artifact(self, artifact: HMLSLArtifact) -> None:
        """
        Ingest an HMLSL artifact into the vector store.
        """
        # Index hierarchy
        self._index_hierarchy(artifact)

        # 1. Index Structural Nodes (Contracts)
        for node in artifact.structural_nodes:
            text = f"Contract: {node.contract_type}\n{str(node.definition)}"
            self._index_item(
                token_id=node.id,
                text=text,
                cluster="structural",
                metadata={"plan_id": artifact.id}
            )

        # 2. Index Behavioral Traces (Execution flow)
        for node in artifact.behavioral_traces:
            text = f"Trace: {node.step_description}"
            if node.result:
                text += f"\nResult: {str(node.result)}"

            tool_name = None
            if node.tool_invocation:
                tool_name = node.tool_invocation.get("tool_name")

            self._index_item(
                token_id=node.id,
                text=text,
                cluster="behavioral",
                metadata={
                    "plan_id": artifact.id,
                    "tool": tool_name
                }
            )

        # 3. Index Visual Persona (Avatar Context)
        for node in artifact.visual_persona_nodes:
            style = node.aesthetic_params.get('style')
            text = f"Persona: {node.cluster_id}\nStyle: {style}"
            self._index_item(
                token_id=node.id,
                text=text,
                cluster="visual",
                metadata={"plan_id": artifact.id}
            )

    def _index_item(
        self,
        token_id: str,
        text: str,
        cluster: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Helper to encode and upsert items."""
        # Use VectorVault's add_entry
        # We map 'cluster' to 'ref_type' in VectorVault for filtering
        self.vector_index.add_entry(
            ref_id=token_id,
            text=text,
            ref_type=cluster,
            metadata=metadata
        )

    def _index_hierarchy(self, artifact: HMLSLArtifact) -> None:
        """
        Builds a simple parent-child index for the artifact.
        Maps plan_id -> [node_ids...]
        """
        plan_id = artifact.id
        self.hierarchy_index.setdefault(
            plan_id, {"structural": [], "behavioral": [], "visual": []}
        )

        for node in artifact.structural_nodes:
            self.hierarchy_index[plan_id]["structural"].append(node.id)
        for node in artifact.behavioral_traces:
            self.hierarchy_index[plan_id]["behavioral"].append(node.id)
        for node in artifact.visual_persona_nodes:
            self.hierarchy_index[plan_id]["visual"].append(node.id)

    def search(
        self, query: str, top_k: int = 5, cluster_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for artifacts.
        """
        # VectorVault search returns List[Tuple[VaultEntry, float]]
        results = self.vector_index.search(
            query=query,
            top_k=top_k,
            ref_type_filter=cluster_filter
        )

        formatted_results = []
        for entry, score in results:
            formatted_results.append({
                "token_id": entry.entry_id,
                "text": entry.embedding.text,
                "score": score,
                "cluster": entry.ref_type,
                "metadata": entry.embedding.metadata
            })

        return formatted_results

    def get_context_hierarchy(self, plan_id: str) -> Dict[str, List[str]]:
        """
        Retrieve the hierarchy of artifacts for a given plan.
        """
        # HMLSL ID format: hmlsl-{plan_id}
        # If passed plain plan_id, try to prepend.
        if plan_id in self.hierarchy_index:
            return self.hierarchy_index[plan_id]

        prefixed_id = f"hmlsl-{plan_id}"
        if prefixed_id in self.hierarchy_index:
            return self.hierarchy_index[prefixed_id]

        return {"error": "Plan hierarchy not found"}
