from __future__ import annotations

from typing import Any, Dict, List, Optional

from orchestrator.ledger_utils import compute_merkle_root
from schemas.hmlsl import (
    BehavioralTraceNode,
    HMLSLArtifact,
    RBACNode,
    SemanticWeightNode,
    StructuralNode,
    VisualPersonaNode,
)


class HMLSLLedgerManager:
    """
    Manages the creation and updates of the HMLSL.
    """
    def __init__(self, plan_id: str):
        self.plan_id = plan_id
        # Initialize an empty artifact structure
        self.structural_nodes: List[StructuralNode] = []
        self.behavioral_traces: List[BehavioralTraceNode] = []
        self.semantic_weights: List[SemanticWeightNode] = []
        self.visual_persona_nodes: List[VisualPersonaNode] = []
        self.rbac_nodes: List[RBACNode] = []
        self.system_invariants: List[str] = [
            "C5_SYMMETRY", "FAIL_CLOSED_GOVERNANCE"
        ]

    def add_structural_node(
        self, contract_type: str, definition: Dict[str, Any]
    ) -> str:
        node = StructuralNode(
            type="StructuralNode",
            contract_type=contract_type,
            definition=definition
        )
        self.structural_nodes.append(node)
        return node.id

    def add_behavioral_trace(
        self,
        step_description: str,
        tool_invocation: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None
    ) -> str:
        node = BehavioralTraceNode(
            type="BehavioralTraceNode",
            step_description=step_description,
            tool_invocation=tool_invocation,
            result=result
        )
        self.behavioral_traces.append(node)
        return node.id

    def _cluster_traces(self) -> Dict[str, List[BehavioralTraceNode]]:
        """
        Self-Clustering: Group traces by tool invocation or type.
        """
        clusters: Dict[str, List[BehavioralTraceNode]] = {}
        for trace in self.behavioral_traces:
            key = "reasoning"
            if trace.tool_invocation:
                key = trace.tool_invocation.get("tool_name", "unknown_tool")
            clusters.setdefault(key, []).append(trace)
        return clusters

    def _assign_semantic_weights(
        self, clusters: Dict[str, List[BehavioralTraceNode]]
    ) -> None:
        """
        Assign Semantic Weights based on cluster density (Resonance).
        """
        total_traces = len(self.behavioral_traces) or 1
        for cluster_key, nodes in clusters.items():
            resonance = len(nodes) / total_traces
            # Simulate manifold coordinates based on resonance
            coords = [resonance, 1.0 - resonance, len(nodes) * 0.1]

            for node in nodes:
                weight_node = SemanticWeightNode(
                    type="SemanticWeightNode",
                    target_node_id=node.id,
                    resonance_score=resonance,
                    manifold_coordinates=coords
                )
                self.semantic_weights.append(weight_node)

    def _generate_visual_persona(
        self, clusters: Dict[str, List[BehavioralTraceNode]]
    ) -> None:
        """
        Generate Visual Persona Nodes based on dominant clusters.
        """
        if not clusters:
            return

        dominant_cluster = max(clusters.items(), key=lambda item: len(item[1]))
        cluster_name, nodes = dominant_cluster

        # Mapping semantic cluster to aesthetic parameters (The "Avatar")
        aesthetic_map = {
            "unity": {"style": "cyberpunk_construct", "color": "#00FF00"},
            "reasoning": {"style": "abstract_geometric", "color": "#0000FF"},
            "threejs": {"style": "wireframe_mesh", "color": "#FF00FF"},
        }
        params = aesthetic_map.get(
            cluster_name,
            {"style": "default_neutral", "color": "#FFFFFF"}
        )

        persona_node = VisualPersonaNode(
            type="VisualPersonaNode",
            cluster_id=cluster_name,
            aesthetic_params=params,
            visual_embedding=[0.1, 0.2, 0.3]  # Placeholder embedding
        )
        self.visual_persona_nodes.append(persona_node)

    def _assign_self_rbac(
        self, clusters: Dict[str, List[BehavioralTraceNode]]
    ) -> None:
        """
        Self-RBAC Assignment: Grant roles based on operational context.
        """
        roles = set()
        justifications = []

        if "unity" in clusters:
            roles.add("UNITY_RENDERER")
            justifications.append("Detected Unity tool usage.")

        if "reasoning" in clusters:
            roles.add("ORCHESTRATOR")
            justifications.append("Detected complex reasoning chains.")

        for role in roles:
            rbac_node = RBACNode(
                type="RBACNode",
                role=role,
                permissions=["execute_tool", "read_memory"],
                justification="; ".join(justifications)
            )
            self.rbac_nodes.append(rbac_node)

    def finalize(self) -> HMLSLArtifact:
        """
        Finalize the ledger:
        1. Perform Self-Clustering.
        2. Assign Semantic Weights.
        3. Generate Visual Persona.
        4. Assign RBAC tokens.
        5. Compute Merkle Root.
        """
        clusters = self._cluster_traces()
        self._assign_semantic_weights(clusters)
        self._generate_visual_persona(clusters)
        self._assign_self_rbac(clusters)

        # Compute Merkle Root of all nodes
        all_nodes = (
            [n.model_dump() for n in self.structural_nodes] +
            [n.model_dump() for n in self.behavioral_traces] +
            [n.model_dump() for n in self.semantic_weights] +
            [n.model_dump() for n in self.visual_persona_nodes] +
            [n.model_dump() for n in self.rbac_nodes]
        )
        merkle_root = compute_merkle_root(all_nodes)

        return HMLSLArtifact(
            id=f"hmlsl-{self.plan_id}",
            structural_nodes=self.structural_nodes,
            behavioral_traces=self.behavioral_traces,
            semantic_weights=self.semantic_weights,
            visual_persona_nodes=self.visual_persona_nodes,
            rbac_nodes=self.rbac_nodes,
            merkle_root=merkle_root,
            system_invariants=self.system_invariants
        )
