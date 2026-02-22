import hashlib

import numpy as np
import pytest

from multi_client_router import (
    ClientNotFound,
    ContaminationError,
    InMemoryEventStore,
    MultiClientMCPRouter,
    QuotaExceededError,
)


@pytest.mark.asyncio
async def test_registers_isolated_client_pipelines() -> None:
    router = MultiClientMCPRouter(InMemoryEventStore())

    await router.register_client("openai-key")
    await router.register_client("anthropic-key")

    oa_key = hashlib.sha256(b"openai-key").hexdigest()[:16]
    cl_key = hashlib.sha256(b"anthropic-key").hexdigest()[:16]

    assert oa_key in router.pipelines
    assert cl_key in router.pipelines

    oa_pipe = router.pipelines[oa_key]
    cl_pipe = router.pipelines[cl_key]

    sample = np.array([0.25, 0.5, 1.0], dtype=float)
    oa_projected = oa_pipe._namespace_embedding(sample)
    cl_projected = cl_pipe._namespace_embedding(sample)

    assert not np.allclose(oa_projected, cl_projected)


@pytest.mark.asyncio
async def test_process_request_applies_baseline_and_witness() -> None:
    router = MultiClientMCPRouter(InMemoryEventStore())
    await router.register_client("openai-key")
    key = hashlib.sha256(b"openai-key").hexdigest()[:16]

    await router.set_client_baseline(key, np.zeros(64, dtype=float))
    result = await router.process_request(key, np.zeros(64, dtype=float))

    assert result["drift"] == 0.0
    assert len(result["sovereignty_hash"]) == 64


@pytest.mark.asyncio
async def test_drift_gate_raises_contamination_error() -> None:
    router = MultiClientMCPRouter(InMemoryEventStore())
    await router.register_client("openai-key")
    key = hashlib.sha256(b"openai-key").hexdigest()[:16]

    await router.set_client_baseline(key, np.zeros(64, dtype=float))

    with pytest.raises(ContaminationError):
        await router.process_request(key, np.ones(64, dtype=float) * 10)


@pytest.mark.asyncio
async def test_quota_enforced_per_client() -> None:
    router = MultiClientMCPRouter(InMemoryEventStore())
    await router.register_client("openai-key", quota=3)
    key = hashlib.sha256(b"openai-key").hexdigest()[:16]
    await router.set_client_baseline(key, np.zeros(1, dtype=float))

    await router.process_request(key, np.array([0.0, 0.0, 0.0]))

    with pytest.raises(QuotaExceededError):
        await router.process_request(key, np.array([0.0]))


@pytest.mark.asyncio
async def test_missing_client_raises_not_found() -> None:
    router = MultiClientMCPRouter(InMemoryEventStore())

    with pytest.raises(ClientNotFound):
        await router.process_request("missing-client", np.array([1.0]))
