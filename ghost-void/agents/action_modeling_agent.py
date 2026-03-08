import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from orchestrator.llm_util import LLMService

class ActionModelingAgent:
    """
    Sub-function of the Orchestration Model.
    Automates the task list by modeling 'task.md' items as GitHub workspace-ready Actions.
    Synchronizes file-based intent with agentic execution state.
    """

    AGENT_NAME = "ActionModelingAgent-GitHub"
    VERSION = "0.1.0"

    def __init__(self, task_file_path: str = "task.md"):
        # Use brain directory task.md if it exists, otherwise fallback
        # In this workspace, let's default to a provided path or look for the first brain dir
        self.task_file_path = Path(task_file_path)
        self.llm = LLMService()

    def set_task_file(self, path: str):
        self.task_file_path = Path(path)

    async def automate_next_task(self) -> Dict[str, str]:
        """
        Reads the task.md file, finds the first uncompleted task,
        and 'models' it into an executable Action.
        """
        if not self.task_file_path.exists():
            return {"status": "ERROR", "message": f"Task file {self.task_file_path} not found."}

        with open(self.task_file_path, "r") as f:
            content = f.read()

        # Regex to find tasks: - [ ] Task name <!-- id: 1 -->
        tasks = re.findall(r"- \[( )\] (.*?) <!-- id: (.*?) -->", content)
        
        if not tasks:
            return {"status": "IDLE", "message": "No pending tasks found."}

        # Take the first uncompleted task
        _, task_name, task_id = tasks[0]
        
        # 'Model' the task as an Action
        prompt = (
            f"SYSTEM: You are the GitHub Actions Modeling Coding Agent.\n"
            f"Transform the following task into a structured 'Working Model Action'.\n\n"
            f"Task: {task_name}\n"
            f"Task ID: {task_id}\n\n"
            f"Output JSON with: 'action_type' (e.g., file_edit, git_commit, docker_build), "
            f"'modeling_logic', and 'github_action_yaml_stub'."
        )

        try:
            modeling_result = self.llm.call_llm(prompt)
            return {
                "status": "ACTION_PENDING",
                "task_id": task_id,
                "task_name": task_name,
                "modeling": modeling_result
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Modeling failed: {str(e)}"}

    def mark_task_complete(self, task_id: str):
        """Standardizes the 'Action' feedback loop by updating the source task file."""
        if not self.task_file_path.exists():
            return

        with open(self.task_file_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if f"<!-- id: {task_id} -->" in line:
                line = line.replace("[ ]", "[x]")
            new_lines.append(line)

        with open(self.task_file_path, "w") as f:
            f.writelines(new_lines)

if __name__ == "__main__":
    # Test script
    import asyncio
    
    async def test():
        # Point to the current project's brain task.md as a test
        agent = ActionModelingAgent()
        # For demo, we'll try to find the brain dir task.md
        # C:\Users\eqhsp\.gemini\antigravity\brain\e87adcde-776c-498f-a0da-d106168504b7\task.md
        brain_task = Path(r"C:\Users\eqhsp\.gemini\antigravity\brain\e87adcde-776c-498f-a0da-d106168504b7\task.md")
        if brain_task.exists():
            agent.set_task_file(str(brain_task))
            print(f"Automating tasks from: {brain_task}")
            result = await agent.automate_next_task()
            print(f"Action Result: {result}")
        else:
            print("No task.md found for testing.")

    asyncio.run(test())
