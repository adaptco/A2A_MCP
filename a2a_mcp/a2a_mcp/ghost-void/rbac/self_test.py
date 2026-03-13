"""
RBAC Self-Test — Autonomous verification of the RBAC system.
This script starts a temporary instance of the RBAC service and verifies
onboarding and permission flows using the RBACClient.
"""

import threading
import time
import requests
import sys
import os
from typing import Dict, Any

# Ensure we can import from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from rbac.rbac_service import app, db
    from rbac.client import RBACClient
    from rbac.persistence import DB_AgentRecord
except ImportError as e:
    print(f"FAILED: Environment issue. Unable to import RBAC modules: {e}")
    sys.exit(1)

def run_service():
    """Run the FastAPI service for testing."""
    import uvicorn
    # Use a high port to avoid conflicts
    uvicorn.run(app, host="127.0.0.1", port=8999, log_level="warning")

def cleanup_db():
    """Wipe the database for a clean test run."""
    session = db.get_session()
    session.query(DB_AgentRecord).delete()
    session.commit()
    session.close()

def main():
    print("=== RBAC SELF-TEST ===")
    
    # 1. Cleanup
    print("[1/5] Cleaning up database...")
    cleanup_db()
    
    # 2. Start Service
    print("[2/5] Starting RBAC service thread...")
    service_thread = threading.Thread(target=run_service, daemon=True)
    service_thread.start()
    
    # Give it a moment to start
    time.sleep(2)
    
    # 3. Initialize Client
    client = RBACClient(base_url="http://127.0.0.1:8999")
    
    # 4. Verify Health
    print("[3/5] Verifying health check...")
    if client.is_healthy():
        print("      PASS: Service is healthy.")
    else:
        print("      FAIL: Service health check failed.")
        sys.exit(1)
        
    # 5. Verify Onboarding & Permissions
    print("[4/5] Verifying onboarding and permissions...")
    try:
        # Onboard an agent
        res = client.onboard_agent(
            agent_id="test-agent-1",
            agent_name="Self Test Agent",
            role="pipeline_operator"
        )
        print(f"      PASS: Agent onboarded. Role: {res.get('role')}")
        
        # Verify permissions
        allowed = client.verify_permission("test-agent-1", action="run_pipeline")
        if allowed:
            print("      PASS: Permission 'run_pipeline' allowed for operator.")
        else:
            print("      FAIL: Permission 'run_pipeline' denied for operator.")
            sys.exit(1)
            
        # Verify denial
        denied = client.verify_permission("test-agent-1", transition="INIT→CONVERGED")
        # pipeline_operator allows many but not INIT->CONVERGED directly in one jump (usually it's multi-step)
        # Checking ROLE_PERMISSIONS: pipeline_operator has INIT->EMBEDDING, etc.
        # Let's check a known denied one:
        denied = client.verify_permission("test-agent-1", transition="FAILED→INIT")
        if not denied:
            print("      PASS: Invalid transition 'FAILED→INIT' correctly denied.")
        else:
            print("      FAIL: Invalid transition 'FAILED→INIT' was allowed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"      FAIL: Exception during verification: {e}")
        sys.exit(1)
        
    print("[5/5] Verifying persistence...")
    # Restart the client logic (service is still running, but let's check if data is there)
    # The database record should still exist.
    session = db.get_session()
    record = session.query(DB_AgentRecord).filter_by(agent_id="test-agent-1").first()
    if record and record.agent_name == "Self Test Agent":
        print("      PASS: Data persisted in SQLite.")
    else:
        print("      FAIL: Persistence verification failed.")
        sys.exit(1)
    session.close()

    print("\nSUCCESS: All RBAC systems are self-running and healthy.")

if __name__ == "__main__":
    main()
