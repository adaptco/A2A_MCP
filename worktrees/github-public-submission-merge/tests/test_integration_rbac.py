"""
Integration Test: RBAC + Orchestrator
Verifies that MCPHub correctly onboards agents and enforces RBAC checks 
during the healing loop.
"""

import asyncio
import threading
import time
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rbac.rbac_service import app, db
from rbac.persistence import DB_AgentRecord
from orchestrator.main import MCPHub

def run_rbac_service():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9002, log_level="warning")

class TestRBACIntegration(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Start RBAC service in thread
        cls.service_thread = threading.Thread(target=run_rbac_service, daemon=True)
        cls.service_thread.start()
        time.sleep(2)  # Wait for startup

    def setUp(self):
        # Cleanup DB
        session = db.get_session()
        session.query(DB_AgentRecord).delete()
        session.commit()
        session.close()

    @patch("orchestrator.llm_util.LLMService.call_llm")
    async def test_healing_loop_with_rbac(self, mock_llm):
        # Setup Mock LLM
        mock_llm.return_value = "Success: code generated"
        
        # Initialize Hub pointing to our test RBAC service
        hub = MCPHub(rbac_url="http://127.0.0.1:9002")
        
        # 1. Test failure without onboarding (fail-closed)
        print("Testing loop without agent onboarding (should fail)...")
        result = await hub.run_healing_loop("Test task", max_retries=1)
        self.assertIsNone(result, "Loop should fail if agents are not onboarded.")

        # 2. Onboard agents
        print("Onboarding agents...")
        hub.onboard_agents()
        
        # 3. Test success with onboarding
        print("Testing loop with agent onboarding (should succeed)...")
        # Mock tester to return PASS after one iteration
        mock_llm.side_effect = [
            "def solution(): pass", # Coder initial
            "This code is great!",   # Tester analysis (no 'error' or 'bug' -> PASS)
        ]
        
        result = await hub.run_healing_loop("Test task", max_retries=1)
        self.assertIsNotNone(result, "Loop should succeed after onboarding.")
        print(f"Integration Success: Artifact {result.artifact_id} generated.")

    @patch("orchestrator.llm_util.LLMService.call_llm")
    async def test_rbac_denial_on_deactivation(self, mock_llm):
        mock_llm.return_value = "def solution(): pass"
        hub = MCPHub(rbac_url="http://127.0.0.1:9002")
        hub.onboard_agents()
        
        # Deactivate tester agent
        from rbac.client import RBACClient
        client = RBACClient(base_url="http://127.0.0.1:9002")
        # Direct session access or client call to deactivate
        session = db.get_session()
        tester = session.query(DB_AgentRecord).filter_by(agent_id="tester-agent-1").first()
        tester.active = False
        session.commit()
        session.close()
        
        print("Testing loop with deactivated tester (should fail)...")
        result = await hub.run_healing_loop("Test task", max_retries=1)
        self.assertIsNone(result, "Loop should fail if agent is deactivated.")

if __name__ == "__main__":
    unittest.main()
