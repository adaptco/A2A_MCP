import asyncio
import json
from pathlib import Path
from orchestrator.intent_engine import IntentEngine

async def demo_task_automation():
    print("--- Initiating Task-to-Action Automation Demo ---")
    
    engine = IntentEngine()
    
    # Use the current project's task list as the target
    # Path: C:\Users\eqhsp\.gemini\antigravity\brain\e87adcde-776c-498f-a0da-d106168504b7\task.md
    task_path = Path(r"C:\Users\eqhsp\.gemini\antigravity\brain\e87adcde-776c-498f-a0da-d106168504b7\task.md")
    
    if not task_path.exists():
        print(f"Error: Task file not found at {task_path}")
        return

    print(f"Target Task List: {task_path}")
    
    # 1. Automate the next task using the 'Working Model' sub-function
    result = await engine.automate_task_action(str(task_path))
    
    print("\n--- Working Model Action (GitHub Actions Compatible) ---")
    if result["status"] == "ACTION_PENDING":
        print(f"Task: {result['task_name']} (ID: {result['task_id']})")
        print("\nModeling Logic:")
        print(result["modeling"])
        
        # In a real workflow, we would now execute the action 
        # (e.g., git commit, code generation, etc.)
        # For the demo, we mark it as modeled and complete in the task list
        # if the user were to proceed.
        print("\n✓ TASK MODELED: Ready for GitHub Action deployment.")
    else:
        print(f"Result: {result['message']}")

if __name__ == "__main__":
    asyncio.run(demo_task_automation())
