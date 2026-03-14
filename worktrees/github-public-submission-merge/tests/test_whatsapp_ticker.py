import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import json
from orchestrator.observers import WhatsAppEventObserver
from orchestrator.storage import PostgresEventStore
from schemas.database import EventModel

@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        # Configure post response
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.HBgLM..."}]}
        mock_response.raise_for_status = MagicMock()
        mock_instance.post.return_value = mock_response
        
        yield mock_instance

@pytest.mark.asyncio
async def test_whatsapp_observer_formats_and_sends_message(mock_httpx_client):
    # Setup
    observer = WhatsAppEventObserver(
        api_token="test_token", 
        phone_id="12345", 
        channel_id="98765"
    )
    
    event = EventModel(
        pipeline="mlops-revenue",
        execution_id="abc1234",
        state="DEPLOYED",
        hash="hash123",
        timestamp=datetime(2026, 2, 16, 14, 0, 0)
    )
    
    # Execute
    await observer.on_state_change(event)
    
    # Verify
    mock_httpx_client.post.assert_called_once()
    call_args = mock_httpx_client.post.call_args
    url = call_args[0][0]
    payload = call_args[1]["json"]
    
    assert url == "https://graph.facebook.com/v20.0/12345/messages"
    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "98765"
    assert "DEPLOYED" in payload["text"]["body"]
    assert "mlops-revenue" in payload["text"]["body"]

@pytest.mark.asyncio
async def test_whatsapp_observer_ignores_non_terminal_states(mock_httpx_client):
    observer = WhatsAppEventObserver("t", "p", "c")
    event = EventModel(state="RUNNING", pipeline="p", execution_id="e")
    
    await observer.on_state_change(event)
    
    mock_httpx_client.post.assert_not_called()

@pytest.mark.asyncio
async def test_postgres_event_store_notifies_observers():
    # Setup Mock DB Manager
    with patch("orchestrator.storage._db_manager") as mock_db_manager:
        mock_db = MagicMock()
        mock_db_manager.SessionLocal.return_value = mock_db
        
        # Setup Observer
        mock_observer = AsyncMock()
        store = PostgresEventStore(observers=[mock_observer])
        
        event_data = {
            "pipeline": "test_pipe",
            "execution_id": "exec_1",
            "state": "DEPLOYED",
            "hash": "h1",
            "details": {"foo": "bar"}
        }
        
        # Execute
        await store.append_event(event_data)
        
        # Verify DB interactions
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Verify Observer Notification
        assert mock_observer.on_state_change.called
        called_event = mock_observer.on_state_change.call_args[0][0]
        assert called_event.state == "DEPLOYED"
        assert called_event.pipeline == "test_pipe"
