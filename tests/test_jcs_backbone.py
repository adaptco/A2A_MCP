import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from core_orchestrator.jcs import (
    DEFAULT_INTEGRITY_LAYERS,
    DEFAULT_SEAL_PROTOCOL,
    DEFAULT_TRIADIC_BACKBONE,
    WORLD_OS_LEDGER_ANCHOR,
)


def test_default_backbone_zero_drift_guards():
    assert DEFAULT_TRIADIC_BACKBONE.zero_drift_attested()


def test_default_backbone_adjacency_contains_all_layers():
    adjacency = DEFAULT_TRIADIC_BACKBONE.as_adjacency()
    # Each defined layer should appear even if it has no outbound edges.
    for layer in DEFAULT_TRIADIC_BACKBONE.layers:
        assert layer in adjacency

    # The Qube core should route feedback to every other layer.
    assert set(adjacency["qube_core"]) == {
        "codex_operational",
        "chatgpt_creative",
        "p3l_philosophical",
    }


def test_ledger_anchor_packet_defaults():
    cycle_id = "attestation-cycle-42"
    packet = DEFAULT_TRIADIC_BACKBONE.ledger_anchor_packet(cycle_id=cycle_id)

    assert packet["ledger_anchor"] == WORLD_OS_LEDGER_ANCHOR
    assert packet["attestation_cycle_id"] == cycle_id
    assert packet["seal_protocol"] == DEFAULT_SEAL_PROTOCOL
    assert packet["triadic_backbone"]["layers"] == DEFAULT_TRIADIC_BACKBONE.layers
    assert packet["integrity_layers"] == DEFAULT_INTEGRITY_LAYERS
    assert packet["zero_drift_guarded"]
