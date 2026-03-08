import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add root path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.gating_agent import GatingAgent
from agents.tester import TesterAgent
from orchestrator.storage import DBManager
from pipeline.lib.canonical import (
    jcs_canonical_bytes,
    sha256_hex,
    compute_doc_id,
    append_to_ledger
)

class TesterModel:
    """
    Unified Tester Model acting as a Network Node.
    Integrates Gating (Security) and Testing (Validation) into the CI/CD loop.
    Anchors all results in a deterministic vector pipeline.
    """
    
    def __init__(self, node_id: str = "NN-7112", ledger_path: str = "ledger/cicd_ledger.jsonl"):
        self.node_id = node_id
        self.ledger_path = ledger_path
        self.gating_agent = GatingAgent()
        self.tester_agent = TesterAgent()
        self.db = DBManager()
        
        # Ensure ledger directory exists
        Path(self.ledger_path).parent.mkdir(parents=True, exist_ok=True)

    async def run_cicd_loop(self, artifact_id: str) -> Dict[str, Any]:
        """
        Executes the full CI/CD loop for a given artifact.
        Token flow is simulated via gating success and vector anchoring.
        """
        print(f"--- [Node {self.node_id}] Initiating CI/CD Flow for {artifact_id} ---")
        
        # 1. Gating Phase (Security & Specification Check)
        gate_result = await self.gating_agent.evaluate_gate(artifact_id, gate_id=f"gate_{self.node_id}")
        
        if gate_result["status"] != "PASS":
            print(f"!!! [Node {self.node_id}] GATE REJECTED: CI/CD Terminated.")
            return self._record_failure(artifact_id, "GATING_FAILED", gate_result)

        # 2. Testing Phase (Logic & Bug Analysis)
        test_report = await self.tester_agent.validate(artifact_id)
        
        if test_report.status != "PASS":
            print(f"!!! [Node {self.node_id}] TEST FAILED: Feedback enqueued for self-healing.")
            # We still proceed to record the attestation in the ledger for transparency
        else:
            print(f"✓ [Node {self.node_id}] TEST PASSED: Promoting artifact...")

        # 3. Vector Pipeline Phase (Deterministic Ledger Attestation)
        attestation = self._create_attestation(artifact_id, gate_result, test_report)
        
        # Canonicalize and Append to Ledger
        ledger_hash = append_to_ledger(attestation, self.ledger_path)
        
        print(f"✓ [Node {self.node_id}] Vector Anchored: {ledger_hash[:16]}...")
        
        return {
            "status": "COMPLETED",
            "artifact_id": artifact_id,
            "gate_status": gate_result["status"],
            "test_status": test_report.status,
            "ledger_hash": ledger_hash,
            "attestation": attestation
        }

    def _create_attestation(self, artifact_id: str, gate_result: Dict, test_report: Any) -> Dict[str, Any]:
        """Creates a deterministic attestation for the vector pipeline."""
        return {
            "version": "1.0.0",
            "node_id": self.node_id,
            "artifact_id": artifact_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attestation_type": "cicd_promotion",
            "proofs": {
                "gate_attestation": gate_result["check_id"],
                "tester_critique_hash": sha256_hex(test_report.critique.encode('utf-8'))
            },
            "status": "VERIFIED" if gate_result["status"] == "PASS" and test_report.status == "PASS" else "COMPROMISED"
        }

    def _record_failure(self, artifact_id: str, reason: str, details: Dict) -> Dict[str, Any]:
        """Records a CI/CD failure without promotion."""
        return {
            "status": "REJECTED",
            "artifact_id": artifact_id,
            "reason": reason,
            "details": details
        }

if __name__ == "__main__":
    # Internal Demo / Test Loop
    async def main():
        # Create a dummy artifact for testing if NONE exists
        db = DBManager()
        from schemas.agent_artifacts import MCPArtifact
        
        test_art_id = f"art-{str(uuid.uuid4())[:8]}"
        art = MCPArtifact(
            artifact_id=test_art_id,
            type="code_solution",
            content="def drift(): print('sliding')",
            agent_name="CoderAgent-SelfTest"
        )
        db.save_artifact(art)
        
        model = TesterModel()
        result = await model.run_cicd_loop(test_art_id)
        print("\nCI/CD Loop Result:")
        print(json.dumps(result, indent=2))

    asyncio.run(main())
