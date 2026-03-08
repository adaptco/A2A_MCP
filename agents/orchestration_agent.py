"""
    Orchestration Agent
    ===================
    Responsible for breaking down high-level project plans into actionable blueprints
    for the specialized agents (Architecture, Coder, Tester).
    """
    import asyncio
    import uuid
    import logging
    import json
    from typing import List
    
    from orchestrator.llm_util import LLMService
    from orchestrator.storage import DBManager
    from schemas.agent_artifacts import MCPArtifact
    from schemas.project_plan import ProjectPlan, PlanAction
    
    logger = logging.getLogger(__name__)
    
    # Pipeline of agents that tasks are delegated to
    AGENT_PIPELINE = ["ArchitectureAgent", "CoderAgent", "TesterAgent"]
    
    class OrchestrationAgent:
        def __init__(self):
            self.llm = LLMService()
            self.db = DBManager()
    
        async def build_blueprint(
            self, 
            project_name: str, 
            task_descriptions: List[str], 
            requester: str = "system"
        ) -> ProjectPlan:
            """
            Constructs a blueprint plan for the project.
            Uses asyncio.to_thread to offload the synchronous blueprint generation
            (which involves blocking DB operations and potential LLM calls) to a separate thread.
            This prevents blocking the main asyncio event loop.
            """
            return await asyncio.to_thread(
                self._build_blueprint_sync,
                project_name,
                task_descriptions,
                requester
            )
    
        def _build_blueprint_sync(
            self, 
            project_name: str, 
            task_descriptions: List[str], 
            requester: str
        ) -> ProjectPlan:
            """Synchronous implementation of blueprint building."""
            plan_id = f"blueprint-{uuid.uuid4()}"
            actions = []
            # Create actions for each task across the pipeline
            for task in task_descriptions:
                for agent_name in AGENT_PIPELINE:
                    action_id = str(uuid.uuid4())
                    # In a full implementation, we might call the LLM here:
                    # instruction = self.llm.call_llm(f"Create instruction for {agent_name} to handle: {task}")
                    # For now, we generate a deterministic instruction.
                    instruction = f"Execute {task} via {agent_name}"
                    action = PlanAction(
                        action_id=action_id,
                        title=f"{agent_name} task",
                        instruction=instruction,
                        status="pending",
                        metadata={"delegated_to": agent_name, "original_task": task}
                    )
                    actions.append(action)
    
            plan = ProjectPlan(
                plan_id=plan_id,
                project_name=project_name,
                requester=requester,
                actions=actions
            )
    
            # Serialize plan content
            if hasattr(plan, "model_dump_json"):
                content_str = plan.model_dump_json()
            elif hasattr(plan, "json"):
                content_str = plan.json()
            else:
                content_str = json.dumps(plan.__dict__, default=str)
    
            # Persist the blueprint artifact (Blocking I/O)
            artifact = MCPArtifact(
                artifact_id=plan_id,
                agent_name="OrchestrationAgent",
                type="blueprint_plan",
                content=content_str,
                version="1.0.0"
            )
            self.db.save_artifact(artifact)
            return plan
    
