"""
RalphAgent — Iterative engineering machine with a Ralph Wiggum personality.
Implements the Pickle Rick lifecycle: PRD -> Breakdown -> Research -> Plan -> Implement -> Refactor.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import PlanAction, ProjectPlan
from schemas.prompt_inputs import PromptIntent


@dataclass
class RalphExecutionState:
    """Tracks the progress of a Ralph iterative loop."""
    phase: str = "PRD"  # PRD, Breakdown, Research, Plan, Implement, Refactor
    iteration: int = 1
    max_iterations: int = 5
    completed_phases: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class RalphAgent:
    """
    An agent that combines Ralph's iterative persistence with Pickle Rick's 
    structured engineering chores.
    """

    AGENT_NAME = "RalphAgent"
    VERSION = "1.0.0"

    # Ralph's Philosophy from the extension
    PHILOSOPHY = (
        "Iteration > Perfection: Don't aim for perfect on first try.\n"
        "Failures Are Data: Use them to improve.\n"
        "Persistence Wins: Keep trying until success.\n"
        "Trust the Process: Don't circumvent with false completion."
    )

    # Pickle Rick's Chores (Lifecycle)
    CHORES = ["PRD", "Breakdown", "Research", "Plan", "Implement", "Refactor"]

    def __init__(self) -> None:
        self.llm = LLMService()
        self.db = DBManager()
        self.state = RalphExecutionState()
        self._ingest_ci_rules()

    def _ingest_ci_rules(self) -> None:
        """Phase 1: Ingest CI rules into agent context."""
        rules = {}
        for path in [".pylintrc", "pyproject.toml"]:
            try:
                with open(path, "r") as f:
                    rules[path] = f.read()
            except FileNotFoundError:
                pass
        
        # Ingest workflow definitions to understand gates
        workflow_dir = ".github/workflows"
        if os.path.exists(workflow_dir):
            for wf in os.listdir(workflow_dir):
                if wf.endswith((".yml", ".yaml")):
                    try:
                        with open(os.path.join(workflow_dir, wf), "r") as f:
                            rules[wf] = f.read()
                    except Exception:
                        pass
        self.state.context["ci_rules"] = rules

    async def execute_task(self, prompt: str, max_iterations: int = 5) -> str:
        """
        Executes a task by iterating through the engineering chores.
        Embodies Ralph's personality while following the strict lifecycle.
        """
        self.state.max_iterations = max_iterations
        self.state.context["original_prompt"] = prompt
        
        report = []
        report.append(f"I'm Ralph! I'm helping! *Iteration {self.state.iteration}*")
        report.append(self.PHILOSOPHY)
        
        while self.state.iteration <= self.state.max_iterations:
            current_chore = self.CHORES[len(self.state.completed_phases) % len(self.CHORES)]
            
            # Execute the current chore
            result = await self._run_chore(current_chore, prompt)
            
            # Phase 2: Local Validation Emulation
            if current_chore == "Implement":
                validation = self._run_local_pylint()
                if "fail" in validation.lower():
                    report.append(f"\n--- Local Pylint Failure (Iteration {self.state.iteration}) ---")
                    report.append(validation)
                    # Force a retry/refactor phase with the feedback
                    self.state.context["pylint_feedback"] = validation
                    self.state.iteration += 1
                    continue

            report.append(f"\n--- Phase: {current_chore} (Iteration {self.state.iteration}) ---")
            report.append(result)
            
            self.state.completed_phases.append(current_chore)
            
            # Check if we've finished all chores in the cycle
            if len(self.state.completed_phases) >= len(self.CHORES):
                report.append("\n<promise>DONE</promise>")
                break
                
            self.state.iteration += 1
            
        return "\n".join(report)

    def _run_local_pylint(self) -> str:
        """Runs pylint on generated artifacts to catch errors before push."""
        import subprocess
        # Scan changed python files or specific directory
        try:
            res = subprocess.run(
                ["pylint", "agents/", "orchestrator/", "app/", "--fail-under=8.0"],
                capture_output=True, text=True
            )
            if res.returncode != 0:
                return f"Pylint failed:\n{res.stdout}\n{res.stderr}"
            return "Pylint passed!"
        except Exception as e:
            return f"Validation error: {str(e)}"

    async def _monitor_github_checks(self, pr_number: int) -> str:
        """Phase 3: Monitor PR status and pull logs on failure."""
        import subprocess
        import json
        
        try:
            # Check PR status
            res = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "statusCheckRollup"],
                capture_output=True, text=True
            )
            data = json.loads(res.stdout)
            failures = [c for c in data.get("statusCheckRollup", []) if c.get("conclusion") == "FAILURE"]
            
            if not failures:
                return "All checks passed!"
                
            feedback = ["GitHub Actions Failures Detected:"]
            for f in failures:
                name = f.get("name")
                # Pull logs for the specific failed check
                log_res = subprocess.run(
                    ["gh", "run", "view", "--log", "-n", name],
                    capture_output=True, text=True
                )
                feedback.append(f"--- Logs for {name} ---\n{log_res.stdout[:2000]}") # Truncate logs
                
            return "\n".join(feedback)
        except Exception as e:
            return f"Error monitoring GitHub: {str(e)}"

    async def _run_chore(self, chore: str, prompt: str) -> str:
        """Runs a specific engineering chore with Ralph's personality."""
        
        chore_prompts = {
            "PRD": "Define the requirements and scope for: {prompt}. Be simple but persistent.",
            "Breakdown": "Break this into atomic tasks for execution: {prompt}.",
            "Research": "Map the codebase and research how to implement: {prompt}.",
            "Plan": "Create a detailed technical implementation plan for: {prompt}.",
            "Implement": "Generate the executable code and tests for: {prompt}.",
            "Refactor": "Clean up the code and remove any slop from: {prompt}."
        }
        
        system_prompt = (
            "You are Ralph Wiggum. You are persistent and love helping. "
            "You say things like 'I'm helping!', 'My cat's breath smells like cat food.', "
            "and 'I'm a unit test!'. You are currently doing the chore: {chore}.\n"
            "Your philosophy is: {philosophy}\n"
            "Workflow constraints:\n"
            "1. You MUST focus EXCLUSIVELY on the {chore} phase.\n"
            "2. Produce high-quality engineering output despite the whimsical persona.\n"
            "Project State: {context}"
        ).format(chore=chore, philosophy=self.PHILOSOPHY, context=self.state.context)

        user_prompt = chore_prompts[chore].format(prompt=prompt)
        
        intent = PromptIntent(
            task_context=f"Project State: {self.state.context}",
            user_input=user_msg,
            workflow_constraints=[
                ralph_persona,
                f"You MUST focus EXCLUSIVELY on the {chore} phase.",
                "Produce high-quality engineering output despite the whimsical persona."
            ],
            metadata={"agent": self.AGENT_NAME, "chore": chore}
        )

        response = await asyncio.to_thread(self.llm.call_llm, prompt_intent=intent)
        
        # Save artifact
        artifact = MCPArtifact(
            artifact_id=f"ralph-{chore.lower()}-{uuid.uuid4().hex[:8]}",
            agent_name=self.AGENT_NAME,
            type=f"ralph_{chore.lower()}",
            content=response,
            metadata={"iteration": self.state.iteration, "chore": chore}
        )
        self.db.save_artifact(artifact)
        
        return response
