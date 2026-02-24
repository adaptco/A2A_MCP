import logging

logger = logging.getLogger(__name__)

class IntentEngine:
    """
    Core engine that orchestrates the agentic pipeline by coordinating
    specialized agents (Architect, Coder, Tester, etc.).
    """
    def __init__(self, architect, coder, tester, reviewer, deployer, manager):
        self.architect = architect
        self.coder = coder
        self.tester = tester
        self.reviewer = reviewer
        self.deployer = deployer
        self.manager = manager

    def run(self, intent: str):
        """
        Executes the pipeline for a given intent.
        """
        logger.info(f"Starting IntentEngine for intent: {intent}")
        
        # 1. Architect analyzes the intent to create a plan
        plan = self.architect.analyze(intent)
        
        # 2. Coder implements the plan
        code = self.coder.implement(plan)
        
        # 3. Tester verifies the code
        test_results = self.tester.test(code)
        
        # 4. Reviewer evaluates code and tests
        review_feedback = self.reviewer.review(code, test_results)
        
        return {
            "status": "success",
            "intent": intent,
            "plan": plan,
            "code": code,
            "test_results": test_results,
            "review_feedback": review_feedback
        }