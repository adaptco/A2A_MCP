import asyncio
from a2a_mcp.event_store import PostgresEventStore

# Helper to run async tests
def run_async(coro):
    return asyncio.run(coro)

def test_initialization():
    async def _test():
        store = PostgresEventStore()
        assert store.events == []
        assert store._last_hash == "0" * 64
        assert store.pool is None
    run_async(_test())

def test_append_event():
    async def _test():
        store = PostgresEventStore()
        payload = {"data": "test_payload"}

        event_hash = await store.append_event(
            tenant_id="tenant_1",
            execution_id="exec_1",
            event_type="test_event",
            payload=payload
        )

        assert len(store.events) == 1
        stored_event = store.events[0]

        assert stored_event["tenant_id"] == "tenant_1"
        assert stored_event["execution_id"] == "exec_1"
        assert stored_event["event_type"] == "test_event"
        assert stored_event["payload"] == payload
        assert stored_event["previous_hash"] == "0" * 64
        assert stored_event["hash"] == event_hash
        assert store._last_hash == event_hash
    run_async(_test())

def test_verify_integrity_valid():
    async def _test():
        store = PostgresEventStore()
        await store.append_event("t1", "e1", "ev1", {"p": 1})
        await store.append_event("t1", "e1", "ev2", {"p": 2})

        is_valid = await store.verify_integrity()
        assert is_valid is True
    run_async(_test())

def test_verify_integrity_tampered_payload():
    async def _test():
        store = PostgresEventStore()
        await store.append_event("t1", "e1", "ev1", {"p": 1})

        # Tamper with the payload
        store.events[0]["payload"]["p"] = 999

        is_valid = await store.verify_integrity()
        assert is_valid is False
    run_async(_test())

def test_verify_integrity_broken_chain():
    async def _test():
        store = PostgresEventStore()
        await store.append_event("t1", "e1", "ev1", {"p": 1})
        hash1 = store.events[0]["hash"]

        await store.append_event("t1", "e1", "ev2", {"p": 2})

        # Tamper with the link
        store.events[1]["previous_hash"] = "0" * 64  # Should be hash1

        is_valid = await store.verify_integrity()
        assert is_valid is False
    run_async(_test())

def test_get_history():
    # get_history is synchronous
    async def _setup():
        store = PostgresEventStore()
        await store.append_event("t1", "e1", "ev1", {"p": 1})
        return store

    store = run_async(_setup())

    history = store.get_history()
    assert len(history) == 1
    assert history[0]["payload"]["p"] == 1

    # Check that modifying history does not affect internal state
    history[0]["payload"]["p"] = 2
    assert store.events[0]["payload"]["p"] == 1

def test_append_multiple_events():
    async def _test():
        store = PostgresEventStore()
        hashes = []
        for i in range(5):
            h = await store.append_event("t1", "e1", "ev", {"i": i})
            hashes.append(h)

        assert len(store.events) == 5
        assert store._last_hash == hashes[-1]

        for i in range(1, 5):
            assert store.events[i]["previous_hash"] == hashes[i-1]
    run_async(_test())

def test_complex_payload():
    async def _test():
        store = PostgresEventStore()
        payload = {
            "nested": {"a": 1, "b": [1, 2, 3]},
            "bool": True,
            "none": None,
            "float": 1.23
        }
        await store.append_event("t1", "e1", "ev", payload)

        assert await store.verify_integrity() is True
        assert store.events[0]["payload"] == payload
    run_async(_test())
