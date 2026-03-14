import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "server" / "goldeneye_mcp_server.py"
SPEC = importlib.util.spec_from_file_location("goldeneye_mcp_server", MODULE_PATH)
game = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = game
SPEC.loader.exec_module(game)


def test_create_join_tick_and_state_flow():
    game._MATCHES.clear()

    created = game.create_match(seed=7)
    assert created["status"] == "ok"
    match_id = created["match_id"]

    joined = game.join_match(match_id, "player")
    assert joined["status"] == "ok"

    control = game.set_player_input(
        match_id,
        "player",
        {"forward": True, "left": False, "right": True, "fire": True},
    )
    assert control["status"] == "ok"

    advanced = game.tick_match(match_id, steps=5)
    assert advanced["status"] == "ok"
    assert advanced["tick"] >= 5

    snapshot = game.get_match_state(match_id)
    assert snapshot["status"] == "ok"
    assert snapshot["match"]["tick"] >= 5
    assert "alpha" in snapshot["match"]["agents"]
    assert "bravo" in snapshot["match"]["agents"]
    assert "player" in snapshot["match"]["agents"]


def test_compliance_roles_validate_remediate_and_gate_levels():
    game._MATCHES.clear()
    match_id = game.create_match(seed=21)["match_id"]

    game.set_agent_drift(match_id, "alpha", symmetry_spokes=6, material="Racing Sand Metallic")

    inspection = game.inspector_validate(match_id)
    assert inspection["status"] == "ok"
    assert inspection["all_compliant"] is False

    blocked = game.negotiator_advance_level(match_id, target_level=2)
    assert blocked["status"] == "blocked"

    remediated = game.corrector_remediate(match_id)
    assert remediated["status"] == "ok"
    assert "alpha" in remediated["remediated_agents"]

    advanced = game.negotiator_advance_level(match_id, target_level=2)
    assert advanced["status"] == "ok"
    assert advanced["new_level"] == 2


def test_unknown_match_errors_are_stable():
    missing = game.get_match_state("does-not-exist")
    assert missing == {"status": "error", "message": "match not found"}
