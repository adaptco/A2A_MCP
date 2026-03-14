import os
import re
import json

class ActionModelingAgent:
    """
    Agent that consumes task.md and generates GitHub-ready modeling actions.
    """
    def __init__(self, task_path="brain/task.md"):
        # Resolve path relative to project root or use provided absolute path
        self.task_path = task_path
        self.actions_dir = ".github/actions/modeling"

    def sync_tasks_to_actions(self):
        """
        Reads task.md and identifies pending tasks to model.
        """
        if not os.path.exists(self.task_path):
            return f"Error: {self.task_path} not found."

        with open(self.task_path, 'r') as f:
            content = f.read()

        # Find pending tasks (e.g., - [ ] Task name <!-- id: 123 -->)
        pending_tasks = re.findall(r'- \[ \] (.*?) <!-- id: (\d+) -->', content)
        
        if not pending_tasks:
            print("ActionModelingAgent: No pending tasks found for modeling.")
            return

        os.makedirs(self.actions_dir, exist_ok=True)
        
        for task_name, task_id in pending_tasks:
            self._create_modeling_action(task_name, task_id)

    def _create_modeling_action(self, name, task_id):
        action_name = name.lower().replace(" ", "_")
        action_path = os.path.join(self.actions_dir, f"{action_name}_v{task_id}.json")
        
        action_schema = {
            "action_id": task_id,
            "name": name,
            "type": "modeling_task",
            "trigger": "manual",
            "capabilities_required": ["static_analysis", "logic_modeling"],
            "output_target": f"modeling_results/{action_name}.md"
        }
        
        with open(action_path, 'w') as f:
            json.dump(action_schema, f, indent=2)
        print(f"ActionModelingAgent: Modeled action '{name}' -> {action_path}")

if __name__ == "__main__":
    # Attempt to find the task file in standard brain directories
    # For now, we mock a path or assume execution from a context where bit is known
    agent = ActionModelingAgent() 
    # Note: In production, path would be passed as arg
    print("ActionModelingAgent: Initialized.")
