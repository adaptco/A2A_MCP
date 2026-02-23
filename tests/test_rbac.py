"""
RBAC Unit Tests — Agent onboarding and permission enforcement.
"""

import pytest
from fastapi.testclient import TestClient

from rbac.rbac_service import app, _registry
from rbac.models import (
    AgentRole,
    ROLE_PERMISSIONS,
    ACTION_PERMISSIONS,
)


@pytest.fixture(autouse=True)
def clear_registry():
    """Reset the in-memory registry between tests."""
    _registry.clear()
    yield
    _registry.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ── Health ───────────────────────────────────────────────────────────────


class TestHealth:
    def test_health_endpoint(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rbac-gateway"

    def test_health_shows_agent_count(self, client):
        assert client.get("/health").json()["registered_agents"] == 0

        client.post("/agents/onboard", json={
            "agent_id": "a1", "agent_name": "Agent 1", "role": "admin"
        })
        assert client.get("/health").json()["registered_agents"] == 1


# ── Onboarding ───────────────────────────────────────────────────────────


class TestOnboarding:
    def test_onboard_admin(self, client):
        r = client.post("/agents/onboard", json={
            "agent_id": "admin-1",
            "agent_name": "Admin Agent",
            "role": "admin",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["agent_id"] == "admin-1"
        assert data["role"] == "admin"
        assert data["onboarded"] is True
        assert len(data["permissions"]) > 0
        assert "run_pipeline" in data["actions"]

    def test_onboard_observer(self, client):
        r = client.post("/agents/onboard", json={
            "agent_id": "obs-1",
            "agent_name": "Observer",
            "role": "observer",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["permissions"] == []   # No transitions allowed
        assert data["actions"] == ["view_artifacts"]

    def test_onboard_pipeline_operator(self, client):
        r = client.post("/agents/onboard", json={
            "agent_id": "op-1",
            "agent_name": "Pipeline Op",
            "role": "pipeline_operator",
        })
        assert r.status_code == 201
        data = r.json()
        assert "INIT→EMBEDDING" in data["permissions"]
        assert "run_pipeline" in data["actions"]

    def test_onboard_duplicate_rejected(self, client):
        client.post("/agents/onboard", json={
            "agent_id": "dup-1", "agent_name": "First", "role": "admin"
        })
        r = client.post("/agents/onboard", json={
            "agent_id": "dup-1", "agent_name": "Duplicate", "role": "observer"
        })
        assert r.status_code == 409

    def test_onboard_with_embedding_config(self, client):
        r = client.post("/agents/onboard", json={
            "agent_id": "embed-1",
            "agent_name": "Embed Agent",
            "role": "pipeline_operator",
            "embedding_config": {"model_id": "all-mpnet-base-v2", "dim": 768},
        })
        assert r.status_code == 201

    def test_onboard_default_role_is_observer(self, client):
        r = client.post("/agents/onboard", json={
            "agent_id": "def-1",
            "agent_name": "Default Role Agent",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "observer"


# ── Permission Checks ────────────────────────────────────────────────────


class TestPermissionChecks:
    def _onboard(self, client, agent_id, role):
        client.post("/agents/onboard", json={
            "agent_id": agent_id, "agent_name": f"Agent {agent_id}", "role": role
        })

    def test_admin_can_do_all_transitions(self, client):
        self._onboard(client, "admin-t", "admin")
        for transition in ROLE_PERMISSIONS[AgentRole.ADMIN]:
            r = client.post("/agents/admin-t/verify", json={
                "agent_id": "admin-t", "transition": transition
            })
            assert r.json()["allowed"] is True, f"Admin should be allowed: {transition}"

    def test_observer_cannot_transition(self, client):
        self._onboard(client, "obs-t", "observer")
        r = client.post("/agents/obs-t/verify", json={
            "agent_id": "obs-t", "transition": "INIT→EMBEDDING"
        })
        assert r.json()["allowed"] is False

    def test_observer_cannot_run_pipeline(self, client):
        self._onboard(client, "obs-act", "observer")
        r = client.post("/agents/obs-act/verify", json={
            "agent_id": "obs-act", "action": "run_pipeline"
        })
        assert r.json()["allowed"] is False

    def test_pipeline_operator_can_run_pipeline(self, client):
        self._onboard(client, "op-act", "pipeline_operator")
        r = client.post("/agents/op-act/verify", json={
            "agent_id": "op-act", "action": "run_pipeline"
        })
        assert r.json()["allowed"] is True

    def test_healer_limited_to_healing_loop(self, client):
        self._onboard(client, "healer-t", "healer")

        # Allowed
        r = client.post("/agents/healer-t/verify", json={
            "agent_id": "healer-t", "transition": "HEALING→LORA_ADAPT"
        })
        assert r.json()["allowed"] is True

        # Not allowed
        r = client.post("/agents/healer-t/verify", json={
            "agent_id": "healer-t", "transition": "INIT→EMBEDDING"
        })
        assert r.json()["allowed"] is False

    def test_unregistered_agent_returns_404(self, client):
        r = client.post("/agents/ghost/verify", json={
            "agent_id": "ghost", "action": "run_pipeline"
        })
        assert r.status_code == 404

    def test_no_action_or_transition_returns_denied(self, client):
        self._onboard(client, "empty-t", "admin")
        r = client.post("/agents/empty-t/verify", json={
            "agent_id": "empty-t"
        })
        assert r.json()["allowed"] is False

    def test_deactivated_agent_denied(self, client):
        self._onboard(client, "deact-t", "admin")
        client.delete("/agents/deact-t")
        r = client.post("/agents/deact-t/verify", json={
            "agent_id": "deact-t", "action": "run_pipeline"
        })
        assert r.json()["allowed"] is False


# ── Agent Management ─────────────────────────────────────────────────────


class TestAgentManagement:
    def test_list_agents_empty(self, client):
        r = client.get("/agents")
        assert r.json()["agents"] == []

    def test_list_agents_after_onboard(self, client):
        client.post("/agents/onboard", json={
            "agent_id": "list-1", "agent_name": "Agent 1", "role": "admin"
        })
        client.post("/agents/onboard", json={
            "agent_id": "list-2", "agent_name": "Agent 2", "role": "observer"
        })
        agents = client.get("/agents").json()["agents"]
        assert len(agents) == 2

    def test_get_permissions(self, client):
        client.post("/agents/onboard", json={
            "agent_id": "perm-1", "agent_name": "Perm Agent", "role": "pipeline_operator"
        })
        r = client.get("/agents/perm-1/permissions")
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "pipeline_operator"
        assert "run_pipeline" in data["actions"]
        assert data["active"] is True

    def test_deactivate_agent(self, client):
        client.post("/agents/onboard", json={
            "agent_id": "deact-1", "agent_name": "To Deactivate", "role": "admin"
        })
        r = client.delete("/agents/deact-1")
        assert r.status_code == 204

        perms = client.get("/agents/deact-1/permissions").json()
        assert perms["active"] is False

    def test_deactivate_nonexistent_returns_404(self, client):
        r = client.delete("/agents/nonexistent")
        assert r.status_code == 404


# ── Permission Matrix Coverage ───────────────────────────────────────────


class TestRolePermissionMatrix:
    """Verify the permission matrix constants are consistent."""

    def test_all_roles_have_permissions(self):
        for role in AgentRole:
            assert role in ROLE_PERMISSIONS
            assert role in ACTION_PERMISSIONS

    def test_admin_is_superset_of_pipeline_operator(self):
        admin = ROLE_PERMISSIONS[AgentRole.ADMIN]
        operator = ROLE_PERMISSIONS[AgentRole.PIPELINE_OPERATOR]
        assert operator.issubset(admin), "Pipeline operator should be a subset of admin"

    def test_admin_is_superset_of_healer(self):
        admin = ROLE_PERMISSIONS[AgentRole.ADMIN]
        healer = ROLE_PERMISSIONS[AgentRole.HEALER]
        assert healer.issubset(admin), "Healer should be a subset of admin"

    def test_observer_has_no_transitions(self):
        assert len(ROLE_PERMISSIONS[AgentRole.OBSERVER]) == 0

    def test_observer_can_only_view(self):
        assert ACTION_PERMISSIONS[AgentRole.OBSERVER] == {"view_artifacts"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
