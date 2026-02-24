"""
LLM Consensus Gate for WHAMEngine.
Enforces multi-model consensus on physical invariants (e.g. C5 symmetry, RSM finish).
"""

from typing import Dict, List, Any, Optional
import hashlib
import json
import asyncio
from dataclasses import dataclass

@dataclass
class ValidationResult:
    passed: bool
    score: float
    model_id: str
    reasoning: str
    metadata: Dict[str, Any]

class LLMConsensusGate:
    """
    Executes parallel validation checks across multiple models/providers.
    Requires a quorum (default 2/3) to generate a sovereignty receipt.
    """

    def __init__(self, required_quorum: float = 0.66):
        self.required_quorum = required_quorum
        self.providers = []  # List of MCP client/provider interfaces

    def register_provider(self, provider_interface: Any):
        """Register a model provider interface."""
        self.providers.append(provider_interface)

    async def validate_invariant(self, artifact_data: Dict[str, Any], invariant_spec: str) -> Dict[str, Any]:
        """
        Run validation across registered providers and check for consensus.

        Args:
            artifact_data: The data/metadata of the artifact to validate.
            invariant_spec: The physical constant/rule to enforce (e.g., "C5 symmetry").

        Returns:
            A receipt dictionary containing the consensus result and Merkle proof.
        """
        if not self.providers:
            # Fallback or error if no providers configured
            return {
                "verified": False,
                "error": "No validation providers registered"
            }

        # Execute parallel checks
        tasks = [p.validate(artifact_data, invariant_spec) for p in self.providers]
        results: List[ValidationResult] = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = [r for r in results if isinstance(r, ValidationResult)]
        passed_count = sum(1 for r in valid_results if r.passed)
        total_valid = len(valid_results)

        if total_valid == 0:
             return {
                "verified": False,
                "error": "All provider checks failed or returned invalid data"
            }

        consensus_reached = (passed_count / total_valid) >= self.required_quorum

        # Build sovereignty receipt
        receipt = {
            "verified": consensus_reached,
            "invariant": invariant_spec,
            "quorum_achieved": f"{passed_count}/{total_valid}",
            "providers": [
                {
                    "model": r.model_id,
                    "passed": r.passed,
                    "reasoning": r.reasoning,
                    # In a real impl, include temperature etc from metadata
                }
                for r in valid_results
            ],
            "merkle_root": self._compute_merkle_root(valid_results)
        }

        return receipt

    def _compute_merkle_root(self, results: List[ValidationResult]) -> str:
        """Compute a simple hash root of the validation results."""
        # Sort to ensure deterministic ordering
        sorted_results = sorted(results, key=lambda x: x.model_id)

        hashes = []
        for r in sorted_results:
            # Canonicalize the result content
            payload = json.dumps({
                "model": r.model_id,
                "passed": r.passed,
                "reasoning": r.reasoning
            }, sort_keys=True)
            hashes.append(hashlib.sha256(payload.encode('utf-8')).hexdigest())

        if not hashes:
            return ""

        # Simplified Merkle root (just hashing the concatenation of leaf hashes for this POC)
        # A real implementation would build the full tree.
        combined = "".join(hashes)
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

# Mock provider for testing/integration
class MockMCPProvider:
    def __init__(self, model_id: str, should_pass: bool = True):
        self.model_id = model_id
        self.should_pass = should_pass

    async def validate(self, data: Any, spec: str) -> ValidationResult:
        # Simulate network delay
        await asyncio.sleep(0.1)
        return ValidationResult(
            passed=self.should_pass,
            score=0.95 if self.should_pass else 0.4,
            model_id=self.model_id,
            reasoning=f"Mock validation for {spec}: {'Passed' if self.should_pass else 'Failed'}",
            metadata={"temperature": 0.7}
        )
