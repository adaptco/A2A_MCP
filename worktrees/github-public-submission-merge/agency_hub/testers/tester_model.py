import hashlib
import json
import os
from agents.gating_agent import GatingAgent
from agents.tester import TesterAgent

class TesterModel:
    """
    Unified Tester Model acting as a secure Network Node for CI/CD.
    """
    def __init__(self):
        self.gating = GatingAgent()
        self.tester = TesterAgent()
        self.ledger_path = "agency_hub/testers/ledger.json"

    def run_cicd_loop(self, component):
        """
        Executes the gating -> testing -> attestation loop.
        """
        print(f"TesterModel: Initiating CI/CD loop for '{component}'...")
        
        # 1. Gating
        gate_verdict = self.gating.validate_action({"component": component, "action": "test"})
        if gate_verdict["verdict"] != "allow":
            return {"status": "blocked", "reason": gate_verdict["reason"]}

        # 2. Testing
        test_results = self.tester.run_tests(component)
        
        # 3. Attestation (Ledger)
        attestation = self._generate_attestation(component, test_results)
        self._log_to_ledger(attestation)

        return {
            "status": "success",
            "test_results": test_results,
            "attestation_hash": attestation["hash"]
        }

    def _generate_attestation(self, component, results):
        payload = {
            "component": component,
            "results": results,
            "timestamp": "2026-02-13T23:35:00Z"
        }
        payload_str = json.dumps(payload, sort_keys=True)
        return {
            "payload": payload,
            "hash": hashlib.sha256(payload_str.encode()).hexdigest()
        }

    def _log_to_ledger(self, attestation):
        ledger = []
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, 'r') as f:
                try:
                    ledger = json.load(f)
                except:
                    pass
        
        ledger.append(attestation)
        with open(self.ledger_path, 'w') as f:
            json.dump(ledger, f, indent=2)
        print(f"TesterModel: Attestation logged to {self.ledger_path}")

if __name__ == "__main__":
    model = TesterModel()
    result = model.run_cicd_loop("ghost-void_engine")
    print(json.dumps(result, indent=2))
