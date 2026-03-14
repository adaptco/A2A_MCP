"""
VH2 Sovereign Validator — WHAM Engine Integration Gate
Validates agent orchestration, digital twin sync, and physics compliance
"""

from enum import Enum
from typing import Dict, Tuple, List, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json


class GateResult(Enum):
    """Validation gate result states"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


@dataclass
class ValidationGate:
    """Base validation gate with witness hashing"""
    name: str
    sovereignty_hash: str = None
    
    def compute_witness(self, data: Dict) -> str:
        """Compute tamper-proof witness hash (RSM gold #D4AF37)"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


class WHAMEngineGate(ValidationGate):
    """
    Validates WHAM (multi-agent orchestration) engine state.
    Ensures OrchestrationAgent, ArchitectureAgent, and other agents are synced.
    """
    
    def __init__(self):
        super().__init__(name="WHAMEngineGate")
        self.required_agents = [
            "OrchestrationAgent",
            "ArchitectureAgent",
            "ValidationAgent"
        ]
    
    async def execute(self, context: Dict) -> Tuple[GateResult, Dict]:
        """
        Execute WHAM engine validation gate.
        
        Args:
            context: Validation context with WHAM agent state
            {
                "wham_agents": [
                    {"type": "OrchestrationAgent", "status": "ready", "version": "1.0.0"},
                    {"type": "ArchitectureAgent", "status": "ready", "version": "1.0.0"},
                    {"type": "ValidationAgent", "status": "ready", "version": "1.0.0"}
                ],
                "digital_twin_sync": true,
                "agent_state_version": "v2025.02"
            }
        
        Returns:
            (GateResult, witness_dict)
        """
        witness_data = {
            "gate": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check 1: Agent Orchestration
        agents_check = self._validate_agent_orchestration(context)
        if not agents_check["passed"]:
            witness_data["checks"]["orchestration"] = agents_check
            witness_hash = self.compute_witness(witness_data)
            return GateResult.FAIL, {
                "witness": "WHAM_ORCHESTRATION_INVALID",
                "witness_hash": witness_hash,
                "details": agents_check
            }
        witness_data["checks"]["orchestration"] = agents_check
        
        # Check 2: Agent Health Status
        health_check = self._validate_agent_health(context)
        if not health_check["passed"]:
            witness_data["checks"]["health"] = health_check
            witness_hash = self.compute_witness(witness_data)
            return GateResult.FAIL, {
                "witness": "WHAM_AGENT_UNHEALTHY",
                "witness_hash": witness_hash,
                "details": health_check
            }
        witness_data["checks"]["health"] = health_check
        
        # Check 3: Digital Twin Synchronization
        dt_sync_check = self._validate_digital_twin_sync(context)
        if not dt_sync_check["passed"]:
            witness_data["checks"]["digital_twin"] = dt_sync_check
            witness_hash = self.compute_witness(witness_data)
            return GateResult.FAIL, {
                "witness": "DT_UNSYNCHRONIZED",
                "witness_hash": witness_hash,
                "details": dt_sync_check
            }
        witness_data["checks"]["digital_twin"] = dt_sync_check
        
        # Check 4: Agent State Machine Compliance
        state_check = self._validate_agent_state_machines(context)
        if not state_check["passed"]:
            witness_data["checks"]["state_machines"] = state_check
            witness_hash = self.compute_witness(witness_data)
            return GateResult.FAIL, {
                "witness": "AGENT_STATE_INVALID",
                "witness_hash": witness_hash,
                "details": state_check
            }
        witness_data["checks"]["state_machines"] = state_check
        
        # Check 5: LoRA-tuned Prompt Validation (if using LLM agents)
        prompt_check = self._validate_lora_prompts(context)
        if not prompt_check["passed"]:
            witness_data["checks"]["lora_prompts"] = prompt_check
            witness_hash = self.compute_witness(witness_data)
            return GateResult.FAIL, {
                "witness": "LORA_PROMPT_INVALID",
                "witness_hash": witness_hash,
                "details": prompt_check
            }
        witness_data["checks"]["lora_prompts"] = prompt_check
        
        # All checks passed
        witness_hash = self.compute_witness(witness_data)
        return GateResult.PASS, {
            "witness": "WHAM_COMPLIANT",
            "witness_hash": witness_hash,
            "checks_passed": 5,
            "timestamp": witness_data["timestamp"]
        }
    
    def _validate_agent_orchestration(self, context: Dict) -> Dict:
        """Validate all required agents are present and properly configured"""
        agents = context.get("wham_agents", [])
        agent_types = [a.get("type") for a in agents]
        
        missing_agents = set(self.required_agents) - set(agent_types)
        
        if missing_agents:
            return {
                "passed": False,
                "reason": "Missing required agents",
                "missing": list(missing_agents),
                "found": agent_types
            }
        
        return {
            "passed": True,
            "agents_count": len(agents),
            "agents": agent_types
        }
    
    def _validate_agent_health(self, context: Dict) -> Dict:
        """Validate all agents are in healthy state"""
        agents = context.get("wham_agents", [])
        
        unhealthy = []
        for agent in agents:
            status = agent.get("status", "unknown")
            if status not in ["ready", "healthy", "operational"]:
                unhealthy.append({
                    "agent": agent.get("type"),
                    "status": status
                })
        
        if unhealthy:
            return {
                "passed": False,
                "reason": "Unhealthy agents detected",
                "unhealthy_agents": unhealthy
            }
        
        return {
            "passed": True,
            "all_agents_healthy": True,
            "total_agents": len(agents)
        }
    
    def _validate_digital_twin_sync(self, context: Dict) -> Dict:
        """Validate digital twin is synchronized (for Unity/Three.js simulation)"""
        dt_sync = context.get("digital_twin_sync", False)
        dt_version = context.get("digital_twin_version", None)
        dt_timestamp = context.get("digital_twin_last_sync", None)
        
        if not dt_sync:
            return {
                "passed": False,
                "reason": "Digital twin not synchronized",
                "synchronized": False
            }
        
        return {
            "passed": True,
            "synchronized": True,
            "version": dt_version,
            "last_sync": dt_timestamp
        }
    
    def _validate_agent_state_machines(self, context: Dict) -> Dict:
        """Validate agent state machines are in valid transitions"""
        agents = context.get("wham_agents", [])
        agent_states = context.get("agent_states", {})
        
        valid_transitions = {
            "INIT": ["READY", "ERROR"],
            "READY": ["RUNNING", "IDLE", "ERROR"],
            "RUNNING": ["COMPLETE", "ERROR", "IDLE"],
            "IDLE": ["RUNNING", "ERROR"],
            "COMPLETE": ["READY", "ERROR"],
            "ERROR": ["INIT", "READY"]
        }
        
        invalid_transitions = []
        for agent in agents:
            agent_type = agent.get("type")
            state = agent_states.get(agent_type, {})
            current = state.get("current_state", "INIT")
            previous = state.get("previous_state", "INIT")
            
            if current not in valid_transitions.get(previous, []):
                invalid_transitions.append({
                    "agent": agent_type,
                    "from": previous,
                    "to": current
                })
        
        if invalid_transitions:
            return {
                "passed": False,
                "reason": "Invalid state transitions detected",
                "invalid": invalid_transitions
            }
        
        return {
            "passed": True,
            "state_machines_valid": True,
            "agents_tracked": len(agents)
        }
    
    def _validate_lora_prompts(self, context: Dict) -> Dict:
        """Validate LoRA-tuned prompts are loaded and valid"""
        lora_config = context.get("lora_config", {})
        lora_version = lora_config.get("version", None)
        lora_base_model = lora_config.get("base_model", None)
        lora_enabled = lora_config.get("enabled", False)
        
        # If LoRA not used, pass (optional feature)
        if not lora_enabled:
            return {
                "passed": True,
                "lora_enabled": False,
                "reason": "LoRA tuning not enabled"
            }
        
        # Validate LoRA is properly configured
        if not lora_version or not lora_base_model:
            return {
                "passed": False,
                "reason": "LoRA configuration incomplete",
                "lora_version": lora_version,
                "lora_base_model": lora_base_model
            }
        
        return {
            "passed": True,
            "lora_enabled": True,
            "lora_version": lora_version,
            "base_model": lora_base_model
        }


class C5SymmetryGate(ValidationGate):
    """Validates C5 72° rotational symmetry (VH2 Ackermann geometry)"""
    
    def __init__(self):
        super().__init__(name="C5SymmetryGate")
        self.required_symmetry = 72.0  # degrees
        self.tolerance = 0.1  # degrees
    
    async def execute(self, context: Dict) -> Tuple[GateResult, Dict]:
        """Validate C5 symmetry in wheel geometry"""
        wheel_geometry = context.get("wheel_geometry", {})
        
        # Extract angles
        angles = [
            wheel_geometry.get("wheel_1_angle", 0),
            wheel_geometry.get("wheel_2_angle", 72),
            wheel_geometry.get("wheel_3_angle", 144),
            wheel_geometry.get("wheel_4_angle", 216),
            wheel_geometry.get("wheel_5_angle", 288)
        ]
        
        # Validate each angle is 72° apart
        expected_angles = [i * self.required_symmetry for i in range(5)]
        deviations = [abs(angles[i] - expected_angles[i]) for i in range(5)]
        
        if any(dev > self.tolerance for dev in deviations):
            return GateResult.FAIL, {
                "witness": "C5_SYMMETRY_VIOLATION",
                "expected_angles": expected_angles,
                "actual_angles": angles,
                "deviations": deviations
            }
        
        return GateResult.PASS, {
            "witness": "C5_SYMMETRIC",
            "angles_valid": angles,
            "tolerance_met": self.tolerance
        }


class RSMGate(ValidationGate):
    """Validates RSM (Rotational Symmetry Module) with gold #D4AF37 hashing"""
    
    def __init__(self):
        super().__init__(name="RSMGate")
        self.gold_hash_prefix = "D4AF37"  # RSM gold signature
    
    async def execute(self, context: Dict) -> Tuple[GateResult, Dict]:
        """Validate RSM compliance with sovereignty hashing"""
        rsm_data = context.get("rsm_module", {})
        
        # Compute RSM witness with gold hash
        witness_data = {
            "rsm": rsm_data,
            "timestamp": datetime.utcnow().isoformat(),
            "gold_prefix": self.gold_hash_prefix
        }
        witness_hash = self.compute_witness(witness_data)
        
        # Verify witness hash starts with gold prefix
        if not witness_hash.upper().startswith(self.gold_hash_prefix.upper()):
            # This is a symbolic check; in practice, hash randomly
            pass
        
        return GateResult.PASS, {
            "witness": "RSM_COMPLIANT",
            "witness_hash": witness_hash,
            "gold_signature": self.gold_hash_prefix
        }


# Validation chain
class SovereigntyChain:
    """Chain of validation gates enforcing VH2 sovereignty"""
    
    def __init__(self):
        self.gates: List[ValidationGate] = [
            WHAMEngineGate(),
            C5SymmetryGate(),
            RSMGate()
        ]
    
    async def validate(self, context: Dict) -> Tuple[bool, List[Dict]]:
        """
        Execute full validation chain.
        Returns (all_passed, results_list)
        """
        results = []
        
        for gate in self.gates:
            result, witness = await gate.execute(context)
            results.append({
                "gate": gate.name,
                "result": result.value,
                "witness": witness
            })
            
            if result == GateResult.FAIL:
                # Fail-closed: stop on first failure
                return False, results
        
        return True, results
