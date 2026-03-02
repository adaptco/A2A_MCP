import asyncio
import os
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, AsyncMock

# Import Simulation Core
from simulation_core.agent_factory import from_prompt
from simulation_core.runtime_engine import tick

# Import Event Store & Integration
from event_store.models import Event
from event_store.postgres_event_store import PostgresEventStore
from integrations.whatsapp_provider import WhatsAppConfig, WhatsAppEventObserver

TENANT_ID = "qube-tenant"

async def append_event_safe(store, tenant_id, execution_id, state, payload):
    """Helper to append event with generated metadata."""
    event = Event(
        execution_id=execution_id,
        event_type="SIMULATION_STEP", # Generalizing for demo
        state=state,
        hash_current=uuid4().hex, # Mocking hash generation for now
        timestamp=datetime.utcnow(),
        payload=payload
    )
    await store.append_event(event)


async def run_demo():
    print("🚀 Starting Verifiable Digital Twin Demo...")

    # 1. Setup Mock Database Pool (since we don't have a real DB connection)
    mock_pool = Mock()
    # Ensure acquire() returns an AsyncMock that can be used as a context manager
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value = mock_conn
    mock_conn.__aenter__.return_value = AsyncMock() # The connection object
    mock_conn.__aexit__.return_value = None

    # 2. Setup WhatsApp Observer
    # Check for env vars, otherwise use dummy values for demo safety
    channel_id = os.getenv("WHATSAPP_CHANNEL_ID", "0029Vb6UzUH5a247SNGocW26")
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "mock_token")

    config = WhatsAppConfig(channel_id=channel_id, access_token=token)
    observer = WhatsAppEventObserver(config)

    # Mock the session/network call if no real token is present to avoid crashing
    if token == "mock_token":
        print("⚠️  No WHATSAPP_ACCESS_TOKEN found. Mocking network calls.")
        mock_session = AsyncMock()
        # Mocking the context manager returned by session.post
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = Mock()
        # session.post() returns a context manager, so we mock the __aenter__ return value
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_resp
        mock_post_ctx.__aexit__.return_value = None
        # Important: session.post() is an async context manager, so calling it returns the context manager
        # But in a mock, if we want `async with session.post(...)`, session.post() is awaited? No.
        # Wait, session.post(...) returns a context manager.
        # The line is: async with self.session.post(...) as resp:
        # So self.session.post(...) is NOT awaited. It is a synchronous call returning an async CM.
        # UNLESS it is a coroutine? No, aiohttp.ClientSession.post is a normal method returning a _RequestContextManager.

        # However, AsyncMock by default makes all methods async (awaitable).
        # So `session.post(...)` becomes a coroutine that must be awaited.
        # But the code uses `async with session.post(...)`. This syntax expects an async context manager,
        # NOT a coroutine that returns an async context manager.

        # We need to make sure session.post is NOT a coroutine but returns the mock_post_ctx.
        mock_session.post = Mock(return_value=mock_post_ctx)
        observer.session = mock_session
    else:
         # Initialize real session if we had a real token (requires running inside an async context usually)
         # For this simple script, we'll manually open/close or let aiohttp create one on fly if designed
         pass


    # 3. Initialize Event Store with Observer
    store = PostgresEventStore(pool=mock_pool, observers=[observer])
    print("✅ Event Store initialized with WhatsApp Observer.")

    # 4. Create Agent from Prompt
    execution_id = f"agent-{uuid4().hex[:8]}"
    description = "a heavy, sluggish agent with high inertia"
    print(f"\n📝 Prompt: '{description}'")

    agent = from_prompt(description)
    print(f"🤖 Agent Created: Mass={agent.mass}, MaxSpeed={agent.max_speed}")

    # 5. Seed Event: AGENT_CREATED
    await append_event_safe(
        store=store,
        tenant_id=TENANT_ID,
        execution_id=execution_id,
        state="AGENT_CREATED",
        payload={
            "description": description,
            "agent_state": agent.to_dict(),
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    # 6. Simulation Loop
    inputs = ["W_pressed", "A_pressed", "W_released", "D_pressed"]
    print(f"\n🎮 Running Simulation Loop ({len(inputs)} ticks)...")

    for input_event in inputs:
        agent, payload = tick(agent, input_event, delta_time=0.016)
        print(f"   Tick: Input={input_event:12} -> Pos=({agent.position.x:.2f}, {agent.position.y:.2f})")

        await append_event_safe(
            store=store,
            tenant_id=TENANT_ID,
            execution_id=execution_id,
            state="RUNNING",
            payload=payload,
        )

    # 7. Finalize and Trigger Witness
    print("\n🏁 Finalizing Execution...")
    await append_event_safe(
        store=store,
        tenant_id=TENANT_ID,
        execution_id=execution_id,
        state="FINALIZED",  # <--- This triggers the WhatsApp Observer
        payload={
            "final_state": agent.to_dict(),
            "finalized_at": datetime.utcnow().isoformat(),
        },
    )

    # Allow async tasks (observer broadcast) to complete
    await asyncio.sleep(0.5)
    print(f"\n✨ Execution {execution_id} completed. WhatsApp witness triggered.")

if __name__ == "__main__":
    asyncio.run(run_demo())
