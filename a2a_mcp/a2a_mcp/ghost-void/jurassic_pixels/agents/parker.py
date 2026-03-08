import json
import random
from typing import List, Dict, Any, Tuple

class Parker:
    def __init__(self, name: str = "Parker"):
        self.name = name
        
        # Personality Traits (0.0 to 1.0)
        self.personality = {
            "Cautious": 0.6,
            "Bold": 0.4,
            "Resourceful": 0.5,
            "Strategic": 0.5,
            "Aggressive": 0.3,
            "Peaceful": 0.7,
            "Explorer": 0.5,
            "Builder": 0.5
        }
        
        # Current Mood
        self.moods = ["Confident", "Anxious", "Curious", "Focused", "Desperate", "Triumphant"]
        self.current_mood = "Curious"
        
        # Contextual Goals
        self.goals = ["Survive", "Escape", "Hunt", "Craft", "Gather", "Build", "Explore", "Dominate"]
        self.current_goal = "Explore"
        
        # Internal State
        self.thoughts: List[str] = []
        self.memories: List[Dict[str, Any]] = []
        self.confidence = 0.5
        self.xp = 0
        
    def think(self, context: str):
        """Generates an internal monologue based on context and personality."""
        thought = f"[{self.current_mood}] {context}"
        if self.personality["Cautious"] > 0.7:
            thought += " - I need to be extremely careful here."
        elif self.personality["Bold"] > 0.7:
            thought += " - This is a great opportunity to show what I've got!"
            
        self.thoughts.append(thought)
        return thought

    def decide_goal(self, state: Dict[str, Any]):
        """Decides the current goal based on state and personality."""
        health = state.get("health", 100)
        threats = state.get("threats", [])
        resources = state.get("resources", {})
        
        if health < 30 or (threats and self.personality["Cautious"] > 0.8):
            self.current_goal = "Survive"
            self.current_mood = "Anxious"
        elif threats and self.personality["Aggressive"] > 0.6:
            self.current_goal = "Hunt"
            self.current_mood = "Focused"
        elif resources.get("wood", 0) > 5 and resources.get("stone", 0) > 3:
            self.current_goal = "Build"
            self.current_mood = "Triumphant"
        else:
            self.current_goal = "Explore"
            self.current_mood = "Curious"
            
        self.think(f"My current goal is to {self.current_goal}")

    def act(self, state: Dict[str, Any], available_actions: List[str]) -> Tuple[str, str]:
        """Chooses an action based on goal, mood, and personality."""
        self.decide_goal(state)
        
        action = random.choice(available_actions) # Placeholder for more complex logic
        
        # Influence action based on goal
        if self.current_goal == "Survive" and "escape" in available_actions:
            action = "escape"
        elif self.current_goal == "Hunt" and "attack" in available_actions:
            action = "attack"
            
        reasoning = f"Reasoning: Goal={self.current_goal}, Mood={self.current_mood}, Action={action}"
        return action, reasoning

    def learn(self, outcome: Dict[str, Any]):
        """Adjusts personality and confidence based on the outcome of an episode."""
        reward = outcome.get("reward", 0)
        survived = outcome.get("survived", False)
        
        if survived:
            self.confidence = min(1.0, self.confidence + 0.05)
            self.xp += reward
            if self.current_goal == "Hunt":
                self.personality["Aggressive"] = min(1.0, self.personality["Aggressive"] + 0.02)
                self.personality["Bold"] = min(1.0, self.personality["Bold"] + 0.01)
            elif self.current_goal == "Build":
                self.personality["Builder"] = min(1.0, self.personality["Builder"] + 0.03)
                self.personality["Resourceful"] = min(1.0, self.personality["Resourceful"] + 0.02)
        else:
            self.confidence = max(0.0, self.confidence - 0.1)
            self.personality["Cautious"] = min(1.0, self.personality["Cautious"] + 0.05)
            self.personality["Bold"] = max(0.0, self.personality["Bold"] - 0.02)

        self.think(f"Episode finished. Reward: {reward}. Survived: {survived}.")

    def save_state(self, filepath: str):
        state = {
            "name": self.name,
            "personality": self.personality,
            "confidence": self.confidence,
            "xp": self.xp,
            "memories": self.memories
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=4)

    @classmethod
    def load_state(cls, filepath: str):
        with open(filepath, "r") as f:
            state = json.load(f)
        parker = cls(state["name"])
        parker.personality = state["personality"]
        parker.confidence = state["confidence"]
        parker.xp = state["xp"]
        parker.memories = state["memories"]
        return parker
