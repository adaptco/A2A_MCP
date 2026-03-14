import asyncio
import re
from pathlib import Path
from orchestrator.intent_engine import IntentEngine
from filesystem_bridge import FileSystemBridge
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutonomousOrchestrator")

class AutonomousOrchestrator:
    def __init__(self, task_file: str, root_dir: str = "."):
        self.task_file = Path(task_file)
        self.root_dir = root_dir
        self.engine = IntentEngine()
        self.bridge = FileSystemBridge()

    def parse_tasks(self):
        """Finds all tasks marked as [ ] in the task file."""
        if not self.task_file.exists():
            logger.error(f"Task file {self.task_file} not found.")
            return []
        
        content = self.task_file.read_text(encoding="utf-8")
        # Match lines like "- [ ] Task description"
        tasks = re.findall(r"- \[ \] (.*)", content)
        return tasks

    def update_task_status(self, task_description: str, success: bool):
        """Updates the status of a task in the task file."""
        content = self.task_file.read_text(encoding="utf-8")
        status_marker = "[x]" if success else "[!]"
        # Escape special characters in task_description for regex
        escaped_task = re.escape(task_description)
        new_content = re.sub(rf"- \[ \] {escaped_task}", f"- {status_marker} {task_description}", content)
        self.task_file.write_text(new_content, encoding="utf-8")
        logger.info(f"Updated task: {task_description} -> {status_marker}")

    async def execute_task(self, task_description: str):
        """Runs the task through the full agentic pipeline."""
        logger.info(f"Starting execution for: {task_description}")
        
        try:
            # Stage 1: Run through IntentEngine
            result = await self.engine.run_full_pipeline(task_description)
            
            if result.success:
                # Stage 2: Apply changes to filesystem
                logger.info(f"Pipeline succeeded for task: {task_description}")
                applied_any = False
                for artifact in result.code_artifacts:
                    logger.info(f"Processing artifact: {artifact.artifact_id} (Type: {artifact.type})")
                    if artifact.type == "code_solution":
                        if self.bridge.apply_changes(artifact.content, self.root_dir):
                            applied_any = True
                
                # If no code was found, we still mark as success if the pipeline says so
                # (e.g., for research tasks)
                self.update_task_status(task_description, True)
                return True
            else:
                logger.error(f"Pipeline failed for task: {task_description}")
                self.update_task_status(task_description, False)
                return False
                
        except Exception as e:
            logger.exception(f"Error executing task {task_description}: {e}")
            self.update_task_status(task_description, False)
            return False

    async def run_all_pending(self):
        """Processes all pending tasks."""
        tasks = self.parse_tasks()
        if not tasks:
            logger.info("No pending tasks found.")
            return

        logger.info(f"Found {len(tasks)} pending tasks.")
        for task in tasks:
            await self.execute_task(task)

if __name__ == "__main__":
    import sys
    task_file_arg = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".gemini" / "antigravity" / "brain" / "84380f26-724c-424f-8829-4869a8233583" / "task.md")
    orchestrator = AutonomousOrchestrator(task_file_arg)
    asyncio.run(orchestrator.run_all_pending())
