"""
Agents module - Agent swarm system for parallel task execution.

Provides specialized agents for research, architecture, coding, and testing.
"""

from .managing_agent import ManagingAgent
from .orchestration_agent import OrchestrationAgent
from .architecture_agent import ArchitectureAgent
from .coder import CoderAgent
from .tester import TesterAgent
from .researcher import ResearcherAgent
from .pinn_agent import PINNAgent
from .notification_agent import NotificationAgent

__all__ = [
    'ManagingAgent',
    'OrchestrationAgent',
    'ArchitectureAgent',
    'CoderAgent',
    'TesterAgent',
    'ResearcherAgent',
    'PINNAgent',
    'NotificationAgent',
]
