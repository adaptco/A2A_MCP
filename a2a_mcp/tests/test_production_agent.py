# tests/test_production_agent.py
"""
Tests for the ProductionAgent.
"""
import pytest

from agents.production_agent import ProductionAgent
from schemas.project_plan import ProjectPlan


def test_create_production_agent():
    """Tests the basic instantiation of the ProductionAgent."""
    agent = ProductionAgent()
    assert agent.AGENT_NAME == "ProductionAgent-Alpha"
    assert agent.VERSION == "1.0.0"


def test_generates_dockerfile_artifact():
    """Tests that the agent generates a valid Dockerfile artifact."""
    agent = ProductionAgent()
    plan = ProjectPlan(
        plan_id="test-plan-123",
        project_name="TestProject",
        requester="test-user",
        actions=[],
    )

    artifact = agent.create_deployment_artifact(plan)

    assert artifact.type == "dockerfile"
    assert "FROM python:3.9-slim" in artifact.content
    assert f"# Dockerfile generated for project: {plan.project_name}" in artifact.content
    assert artifact.metadata["agent"] == agent.AGENT_NAME
    assert artifact.metadata["plan_id"] == plan.plan_id

