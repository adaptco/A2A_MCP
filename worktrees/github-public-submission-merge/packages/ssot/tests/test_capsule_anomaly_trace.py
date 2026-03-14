"""Tests for the anomaly trace capsule protocol scaffold."""

from __future__ import annotations

import json

import pytest

from capsule.anomaly.trace.v1 import (
    AnomalyTraceProtocol,
    Attestation,
    DEFAULT_PROTOCOL,
    EmissionArc,
    FallbackArc,
    RecoveryGlyph,
    Response,
    TransitNode,
    Trigger,
    VisualGrammar,
    default_protocol,
    default_protocol_dict,
    default_protocol_json,
    load_protocol_resource,
)


@pytest.fixture(scope="module")
def expected_payload() -> dict[str, object]:
    """Canonical payload mirrored from the fossilized JSON resource."""

    return {
        "capsuleId": "capsule.anomaly.trace.v1",
        "title": "Anomaly Trace Protocol",
        "description": (
            "Encodes rupture-grade emissions into scrollstream-valid artifacts for replay, "
            "contributor training, and forensic lineage mapping."
        ),
        "trigger": {
            "source": "HUD emission",
            "condition": "glyph integrity breach",
            "sector": "braid sector 3",
            "severity": "high",
        },
        "response": {
            "fallbackArc": {
                "color": "amber",
                "structure": "braided",
                "stabilization": "glitch-corrected",
                "rhythm": "triple-beat",
            },
            "recoveryGlyph": {
                "status": "embedded",
                "location": "scrollstream rail",
                "annotation": "rupture trace",
                "alertFlag": True,
            },
        },
        "visualGrammar": {
            "emissionArc": {
                "tone": "Shout",
                "gesture": "Signal_Broadcast",
                "shimmer": "high-frequency crackle",
                "trail": "glyph fragments",
            },
            "transitNode": {
                "collision": "glyph firewall",
                "reaction": "tri-glyph bloom",
                "reroute": "anomaly trace channel",
            },
        },
        "attestation": {
            "emotionallyLayered": True,
            "sceneAware": True,
            "replayReady": True,
            "contributorTrainable": True,
        },
        "status": "fossilized",
    }


def test_default_protocol_identity() -> None:
    """The helper should always return the canonical protocol singleton."""

    protocol = default_protocol()
    assert protocol is DEFAULT_PROTOCOL
    assert isinstance(protocol, AnomalyTraceProtocol)
    assert protocol.capsuleId == "capsule.anomaly.trace.v1"


def test_protocol_structure_types() -> None:
    """Nested structures should resolve to the dedicated dataclasses."""

    protocol = default_protocol()
    assert isinstance(protocol.trigger, Trigger)
    assert isinstance(protocol.response, Response)
    assert isinstance(protocol.response.fallbackArc, FallbackArc)
    assert isinstance(protocol.response.recoveryGlyph, RecoveryGlyph)
    assert isinstance(protocol.visualGrammar, VisualGrammar)
    assert isinstance(protocol.visualGrammar.emissionArc, EmissionArc)
    assert isinstance(protocol.visualGrammar.transitNode, TransitNode)
    assert isinstance(protocol.attestation, Attestation)


def test_protocol_dict_matches_expected(expected_payload: dict[str, object]) -> None:
    """The dictionary representation should mirror the JSON payload."""

    assert default_protocol_dict() == expected_payload
    assert default_protocol().to_dict() == expected_payload


def test_protocol_json_round_trip(expected_payload: dict[str, object]) -> None:
    """JSON helper should serialize to a loadable payload."""

    payload_json = default_protocol_json(indent=2)
    assert json.loads(payload_json) == expected_payload


def test_resource_payload_matches(expected_payload: dict[str, object]) -> None:
    """The bundled JSON resource should stay aligned with the dataclass payload."""

    assert load_protocol_resource() == expected_payload
