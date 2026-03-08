import sys
import os

# Add the tools directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))

from qube.qube_mcp import dock_model, get_state, execute_action

print("--- Qube Bridge Verification ---")

# 1. Test Docking
print("\n[1] Testing 'dock_model'...")
dock_result = dock_model()
print(f"Result: {dock_result}")

# 2. Test Get State
print("\n[2] Testing 'get_state'...")
state_result = get_state()
print(f"Result: {state_result}")

# 3. Test Action
print("\n[3] Testing 'execute_action'...")
action_result = execute_action("SIM_CITY", '{"cycles": 10}')
print(f"Result: {action_result}")

print("\n--- Verification Complete ---")
