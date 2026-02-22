"""
Routing module for Career Dreamer Blue/Green dot logic using a Mixture of Experts pattern.

- Blue Dot (database-sourced) entries route to `DatabaseExpert`
- Green Dot (AI-generated/Gemini) entries route to `GeminiExpert`
"""

import logging
from typing import Any, Dict, Protocol

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CareerAgent(Protocol):
    """Interface for expert agents in the career routing MoE."""

    def process(self, career_data: Dict[str, Any]) -> str:
        """Process a career entry and return a response string."""
        ...


class DatabaseExpert:
    """
    Handles database-sourced careers (Blue Dots).

    Specialty: retrieving structured facts (salary, requirements, outlook) from the US occupation database.
    """

    def process(self, career_data: Dict[str, Any]) -> str:
        role = career_data.get("role_name", "(unknown role)")
        return (
            f"[Database Expert] Retrieved structured data for '{role}': "
            "Avg Salary: $XX,XXX | Education: Bachelor's | Outlook: Stable."
        )


class GeminiExpert:
    """
    Handles AI-generated ideas (Green Dots).

    Specialty: brainstorming, chatting, and exploring creative AI-generated career suggestions.
    """

    def process(self, career_data: Dict[str, Any]) -> str:
        role = career_data.get("role_name", "(unknown role)")
        return (
            f"[Gemini Expert] Initiating chat for generated idea '{role}'. "
            "Let's explore why this might fit your creative profile..."
        )


def route_task(career_entry: Dict[str, Any], agents: Dict[str, CareerAgent]) -> CareerAgent:
    """
    Route based on source type:

    - `database` (Blue Dot) -> DatabaseExpert
    - `gemini` (Green Dot) -> GeminiExpert
    """

    source_type = career_entry.get("source_type")

    if source_type == "database":
        logger.info("Routing '%s' to DATABASE expert (Blue Dot logic)", career_entry.get("role_name"))
        return agents["database"]

    if source_type == "gemini":
        logger.info("Routing '%s' to GEMINI expert (Green Dot logic)", career_entry.get("role_name"))
        return agents["gemini"]

    raise ValueError(f"Unknown source type: {source_type}")


class MoEController:
    """Controller that owns expert agents and dispatches requests."""

    def __init__(self) -> None:
        self.agents: Dict[str, CareerAgent] = {
            "database": DatabaseExpert(),
            "gemini": GeminiExpert(),
        }

    def handle_request(self, career_data: Dict[str, Any]) -> None:
        try:
            selected_agent = route_task(career_data, self.agents)
            result = selected_agent.process(career_data)
            print(result)
        except Exception as exc:  # noqa: BLE001
            logger.error("Error in MoE Controller: %s", exc)


if __name__ == "__main__":
    moe = MoEController()

    blue_dot_task = {"role_name": "Mechanical Engineer", "source_type": "database", "id": 101}
    green_dot_task = {"role_name": "Eco-Friendly Urban Planner", "source_type": "gemini", "id": 202}

    print("--- Processing Task 1 ---")
    moe.handle_request(blue_dot_task)

    print("\n--- Processing Task 2 ---")
    moe.handle_request(green_dot_task)
