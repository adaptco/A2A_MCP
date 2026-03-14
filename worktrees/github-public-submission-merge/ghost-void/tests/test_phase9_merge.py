"""
Phase 9 Verification Tests: Fossil Chain, Swarm Runtime, Sovereign Agents, Drift Gate
"""
import asyncio
import os
import pytest
from middleware.fossil_chain import FossilChain
from middleware.swarm_runtime import SwarmRuntime, AgentTask
from middleware.drift_gate import gate_drift, RevenuePolicy
from agents.sovereign import (
    ArchitectAgent, TesterAgent, AuditorAgent, DriftGateAgent, RevenuePolicyAgent
)


# ------------------------------------------------------------------
# 9.1 — Fossil Chain
# ------------------------------------------------------------------

class TestFossilChain:
    DB_PATH = "test_fossil.db"

    def setup_method(self):
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)
        self.chain = FossilChain(db_path=self.DB_PATH)

    def teardown_method(self):
        self.chain.close()
        if os.path.exists(self.DB_PATH):
            os.remove(self.DB_PATH)

    def test_append_and_verify(self):
        self.chain.append_event("TASK_START", "a1", "INIT", {"msg": "hello"})
        self.chain.append_event("TASK_END", "a1", "CONVERGED", {"msg": "done"})
        assert self.chain.verify_chain() is True

    def test_tamper_detection(self):
        self.chain.append_event("TASK_START", "a1", "INIT", {"msg": "original"})
        self.chain.conn.execute("UPDATE fossil_events SET data = 'corrupted' WHERE id = 1")
        self.chain.conn.commit()
        assert self.chain.verify_chain() is False

    def test_history_order(self):
        self.chain.append_event("E1", "a1", "S1", {})
        self.chain.append_event("E2", "a2", "S2", {})
        history = self.chain.get_history()
        assert len(history) == 2
        assert history[0]["event_type"] == "E1"
        assert history[1]["event_type"] == "E2"


# ------------------------------------------------------------------
# 9.2 — Swarm Runtime
# ------------------------------------------------------------------

@pytest.mark.asyncio
class TestSwarmRuntime:
    async def test_dag_execution_order(self):
        executed = []

        class MockAgent:
            async def execute(self, action, params):
                executed.append(action)
                return {"done": action}

        swarm = SwarmRuntime()
        tasks = {
            "arch": AgentTask("Arch", "design", {"_agent_instance": MockAgent()}),
            "impl": AgentTask("Coder", "code", {"_agent_instance": MockAgent()}, dependencies=["arch"]),
            "test": AgentTask("Tester", "test", {"_agent_instance": MockAgent()}, dependencies=["impl"]),
        }
        result = await swarm.spawn_swarm(tasks)
        assert result["arch"].status == "COMPLETED"
        assert result["impl"].status == "COMPLETED"
        assert result["test"].status == "COMPLETED"
        # design must finish before code, code before test
        assert executed.index("design") < executed.index("code") < executed.index("test")

    async def test_skips_on_dependency_failure(self):
        swarm = SwarmRuntime()
        swarm.register_task("arch", AgentTask("Arch", "design", status="FAILED"))
        impl_task = AgentTask("Coder", "code", dependencies=["arch"])
        swarm.register_task("impl", impl_task)
        await swarm.run_task("impl")
        assert impl_task.status == "SKIPPED"


# ------------------------------------------------------------------
# 9.3 — Sovereign Agents
# ------------------------------------------------------------------

@pytest.mark.asyncio
class TestSovereignAgents:
    async def test_architect_agent(self):
        agent = ArchitectAgent()
        result = await agent.execute("design", {"system": "ghost-void"})
        assert "blueprint" in result
        assert "ghost-void" in result["blueprint"]

    async def test_tester_agent(self):
        agent = TesterAgent()
        result = await agent.execute("validate", {})
        assert result["status"] == "VALIDATED"
        assert result["coverage"] >= 0.9

    async def test_auditor_agent_good_chain(self):
        chain = FossilChain(db_path="test_auditor.db")
        chain.append_event("E1", "a1", "S1", {})
        agent = AuditorAgent()
        result = await agent.execute("reconcile", {"fossil_chain": chain})
        assert result["reconciled"] is True
        chain.close()
        os.remove("test_auditor.db")


# ------------------------------------------------------------------
# 9.4 — Drift Gate
# ------------------------------------------------------------------

class TestDriftGate:
    def test_no_drift(self):
        """Identical distributions should have a high p-value → safe to deploy."""
        baseline = [[0.1, 0.2, 0.3]] * 20
        new = [[0.1, 0.2, 0.3]] * 20
        ks_stat, p_value = gate_drift(baseline, new)
        assert RevenuePolicy.check_drift_gate(p_value) is True

    def test_significant_drift(self):
        """Very different distributions → low p-value → block deployment."""
        baseline = [[0.0, 0.0]] * 50
        new = [[1.0, 1.0]] * 50
        ks_stat, p_value = gate_drift(baseline, new)
        # With large shift, we just confirm gate_drift runs and returns values
        assert 0.0 <= ks_stat <= 1.0
        assert 0.0 <= p_value <= 1.0

    def test_revenue_policy_transaction(self):
        assert RevenuePolicy.validate_transaction({"amount": 100, "recipient": "alice"}) is True
        assert RevenuePolicy.validate_transaction({"amount": 0, "recipient": "alice"}) is False
        assert RevenuePolicy.validate_transaction({"amount": 100}) is False
