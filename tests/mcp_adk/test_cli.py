import json
from pathlib import Path

from mcp_adk.cli import main


def test_generate_python_agent(tmp_path: Path) -> None:
    target = tmp_path / "sample_agent"
    exit_code = main(["generate", "python-agent", str(target)])
    assert exit_code == 0
    assert (target / "agent.py").exists()
    assert (target / "handlers" / "on_event.py").exists()


def test_validate_contract(tmp_path: Path) -> None:
    contract = {
        "trigger_reason": "drift_detected",
        "mode": "hermetic",
        "policy_zone": "default",
        "required_checks": ["pytest"],
        "max_entropy_budget": {"max_diff_size": 100, "allow_dependency_changes": False},
        "acceptance_invariants": ["policy_zoning"],
    }
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")

    exit_code = main(["validate", "contract", str(path)])
    assert exit_code == 0
