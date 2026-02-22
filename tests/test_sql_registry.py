import pytest
from rbac.models import AgentRecord, AgentRole
from rbac.storage import SQLAgentRegistry

@pytest.fixture
def sql_registry(tmp_path):
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    return SQLAgentRegistry(db_url)

def test_sql_registry_crud(sql_registry):
    # Create
    record = AgentRecord(
        agent_id="agent-1",
        agent_name="Test Agent",
        role=AgentRole.ADMIN,
        embedding_config={"dim": 128},
        active=True
    )
    sql_registry.register(record)

    # Read
    fetched = sql_registry.get("agent-1")
    assert fetched is not None
    assert fetched.agent_id == "agent-1"
    assert fetched.role == AgentRole.ADMIN
    assert fetched.embedding_config == {"dim": 128}

    # List
    all_agents = sql_registry.list_all()
    assert len(all_agents) == 1
    assert all_agents[0].agent_id == "agent-1"

    # Update
    record.agent_name = "Updated Name"
    sql_registry.register(record)
    fetched = sql_registry.get("agent-1")
    assert fetched.agent_name == "Updated Name"

    # Deactivate
    sql_registry.deactivate("agent-1")
    fetched = sql_registry.get("agent-1")
    assert fetched.active is False

    # Count
    assert sql_registry.count() == 1
