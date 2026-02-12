# inside IntentEngine
async def process_plan(self, plan):
    # existing logic...
    artifacts = []
    # before generating: ensure state machine exists and we were called by sm callback
    artifact = await self.coder.generate_solution(parent_id=plan.plan_id, feedback=None)
    # persist artifact
    self.db.save_artifact(artifact)
    # automatically invoke tester and then return
    report = await self.tester.validate(artifact.artifact_id)
    return artifacts
