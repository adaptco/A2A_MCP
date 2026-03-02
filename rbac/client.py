"""
RBAC Client — Lightweight HTTP client for the orchestrator to call the RBAC gateway.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class RBACClient:
    """
    Synchronous HTTP client for the RBAC gateway.

    Usage:
        client = RBACClient("http://rbac-gateway:8001")
        result = client.onboard_agent("agent-1", "ManagingAgent", "pipeline_operator")
        allowed = client.verify_permission("agent-1", action="run_pipeline")
    """

    def __init__(self, base_url: str = "http://localhost:8001", timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Health ───────────────────────────────────────────────────────

    def is_healthy(self) -> bool:
        """Check if the RBAC gateway is reachable."""
        try:
            r = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    # ── Onboarding ───────────────────────────────────────────────────

    def onboard_agent(
        self,
        agent_id: str,
        agent_name: str,
        role: str = "observer",
        embedding_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register a new agent with the RBAC gateway.

        Returns the OnboardingResult dict on success.
        Raises RuntimeError on failure.
        """
        payload = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "role": role,
            "embedding_config": embedding_config or {},
            "metadata": metadata or {},
        }

        try:
            r = requests.post(
                f"{self.base_url}/agents/onboard",
                json=payload,
                timeout=self.timeout,
            )
            if r.status_code == 201:
                return r.json()
            elif r.status_code == 409:
                logger.info("Agent '%s' already onboarded.", agent_id)
                return {"agent_id": agent_id, "onboarded": False, "detail": "already_exists"}
            else:
                r.raise_for_status()
        except requests.RequestException as e:
            logger.warning("RBAC onboarding failed for '%s': %s", agent_id, e)
            raise RuntimeError(f"RBAC onboarding failed: {e}") from e

        return {}  # unreachable, satisfies type checker

    # ── Permission checks ────────────────────────────────────────────

    def verify_permission(
        self,
        agent_id: str,
        action: Optional[str] = None,
        transition: Optional[str] = None,
    ) -> bool:
        """
        Check if the agent is allowed to perform an action or transition.

        Returns True if allowed, False otherwise.
        On network failure, logs a warning and returns False (fail-closed).
        """
        payload: Dict[str, Any] = {"agent_id": agent_id}
        if action:
            payload["action"] = action
        if transition:
            payload["transition"] = transition

        try:
            r = requests.post(
                f"{self.base_url}/agents/{agent_id}/verify",
                json=payload,
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return r.json().get("allowed", False)
            elif r.status_code == 404:
                logger.warning("Agent '%s' not registered in RBAC.", agent_id)
                return False
            else:
                r.raise_for_status()
        except requests.RequestException as e:
            logger.warning("RBAC check failed for '%s': %s (fail-closed)", agent_id, e)
            return False

        return False

    # ── Query ────────────────────────────────────────────────────────

    def get_permissions(self, agent_id: str) -> Dict[str, Any]:
        """Fetch the full permission scope for an agent."""
        try:
            r = requests.get(
                f"{self.base_url}/agents/{agent_id}/permissions",
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.warning("Failed to fetch permissions for '%s': %s", agent_id, e)
            return {}
