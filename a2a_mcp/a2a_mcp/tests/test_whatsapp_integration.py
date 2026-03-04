import asyncio
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime
from event_store.models import Event
from event_store.postgres_event_store import PostgresEventStore
from integrations.whatsapp_provider import WhatsAppEventObserver, WhatsAppConfig

@pytest.mark.asyncio
async def test_whatsapp_integration_flow():
    # 1. Setup Config & Observer
    config = WhatsAppConfig(
        channel_id="0029Vb6UzUH5a247SNGocW26",
        access_token="test_token"
    )
    observer = WhatsAppEventObserver(config)

    # 2. Mock aiohttp session to prevent actual network calls
    mock_session = AsyncMock()
    # The return value of post() is a context manager, so we mock __aenter__
    # This chain handles: async with session.post(...) as resp:
    mock_response = AsyncMock()
    mock_response.raise_for_status = Mock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    observer.session = mock_session

    # 3. Setup Event Store
    mock_pool = Mock()
    event_store = PostgresEventStore(pool=mock_pool, observers=[observer])

    # 4. Create a Test Event (Terminal State)
    event = Event(
        execution_id="exec-123",
        event_type="MLOPS_DEPLOY",
        state="DEPLOYED",
        hash_current="hash_12345",
        timestamp=datetime(2023, 10, 26, 12, 0, 0)
    )

    # 5. Trigger Append
    await event_store.append_event(event)

    # 6. Verify Observer was called and broadcast task created
    # Since _broadcast is fire-and-forget via asyncio.create_task,
    # we need to yield to the event loop to let it run.
    # We loop briefly to allow the task to be scheduled and run.
    await asyncio.sleep(0.1)

    # 7. Assert Mock Session Call
    mock_session.post.assert_called_once()

    # Verify URL and Headers
    args, kwargs = mock_session.post.call_args
    assert args[0] == "https://graph.facebook.com/v20.0/0029Vb6UzUH5a247SNGocW26/messages"
    assert kwargs["headers"]["Authorization"] == "Bearer test_token"

    # Verify Payload Body
    payload = kwargs["json"]
    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "0029Vb6UzUH5a247SNGocW26"

    # Verify content in the body
    body_text = payload["text"]["body"]
    assert "exec-123" in body_text
    assert "DEPLOYED" in body_text
    assert "hash_12345" in body_text

@pytest.mark.asyncio
async def test_whatsapp_observer_ignores_non_terminal_states():
    config = WhatsAppConfig(
        channel_id="test_channel",
        access_token="test_token"
    )
    observer = WhatsAppEventObserver(config)

    mock_session = AsyncMock()
    observer.session = mock_session

    event = Event(
        execution_id="exec-456",
        event_type="MLOPS_RUN",
        state="RUNNING", # Non-terminal
        hash_current="hash_456",
        timestamp=datetime.now()
    )

    # This should return immediately and NOT create a task
    await observer.on_state_change(event)

    # Yield to be sure
    await asyncio.sleep(0.01)

    # Should NOT call post
    mock_session.post.assert_not_called()
