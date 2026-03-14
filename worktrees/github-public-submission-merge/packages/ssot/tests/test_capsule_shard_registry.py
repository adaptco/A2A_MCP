import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from capsule.shard.registry.v1 import Shard, ShardLifecycleEvent, ShardRegistry


@pytest.fixture
def shard():
    shard = Shard(
        shard_id="braid:alpha",
        overlay_signature="spark-attestation-01",
        emotional_payload_map={"rupture": "reflect"},
    )
    return shard


def test_shard_validate_overlay(shard):
    assert shard.validate_overlay("spark-attestation-01")
    assert not shard.validate_overlay("spark-attestation-99")


def test_register_and_trigger_hooks(shard):
    events = []

    def on_emit(s):
        events.append((ShardLifecycleEvent.EMIT, s.shard_id))

    shard.register_hook(ShardLifecycleEvent.EMIT, on_emit)
    shard.emit()

    assert events == [(ShardLifecycleEvent.EMIT, "braid:alpha")]


def test_register_hook_requires_callable(shard):
    with pytest.raises(TypeError):
        shard.register_hook(ShardLifecycleEvent.EMIT, None)  # type: ignore[arg-type]


def test_registry_register_and_require(shard):
    registry = ShardRegistry()
    registry.register(shard)

    assert registry.require("braid:alpha") is shard
    assert "braid:alpha" in registry


def test_registry_register_duplicate(shard):
    registry = ShardRegistry()
    registry.register(shard)
    with pytest.raises(ValueError):
        registry.register(shard)


def test_registry_overlay_enforcement(shard):
    registry = ShardRegistry()
    registry.register(shard)

    assert registry.ensure_overlay("braid:alpha", "spark-attestation-01") is shard

    with pytest.raises(PermissionError):
        registry.ensure_overlay("braid:alpha", "spark-attestation-02")


def test_registry_trigger_with_overlay(shard):
    registry = ShardRegistry()
    registry.register(shard)

    events = []

    shard.register_hook("on_restore", lambda s: events.append(s.shard_id))

    registry.trigger(
        "braid:alpha",
        ShardLifecycleEvent.RESTORE,
        overlay_signature="spark-attestation-01",
    )

    assert events == ["braid:alpha"]

    with pytest.raises(PermissionError):
        registry.trigger(
            "braid:alpha",
            ShardLifecycleEvent.RESTORE,
            overlay_signature="spark-attestation-02",
        )


def test_registry_require_missing():
    registry = ShardRegistry()
    with pytest.raises(KeyError):
        registry.require("missing-shard")

