
from agents.coder import CoderAgent
from agents.tester import TesterAgent
from agents.gemini_agent import GeminiAgent

class AgentHub:
    """
    Central hub for managing and initializing agent instances.
    """
    def __init__(self, runtime=None):
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.gemini = GeminiAgent(runtime=runtime) if runtime else None

    def get_agent(self, agent_name: str):
        if agent_name == "coder":
            return self.coder
        elif agent_name == "tester":
            return self.tester
        elif agent_name == "gemini":
            return self.gemini
        return None
