from __future__ import annotations

import pytest

from orchestrator.option_b import OptionBConfigError, OptionBService, parse_command


def test_parse_command_supported_variants() -> None:
    triage = parse_command("!triage", "investigate logs")
    assert triage.normalized_command == "!triage"
    assert triage.operation == "triage"
    assert triage.args == "investigate logs"
    assert triage.description == "triage investigate logs"

    run_inline = parse_command("run smoke tests")
    assert run_inline.normalized_command == "!run"
    assert run_inline.operation == "run"
    assert run_inline.args == "smoke tests"

    deploy = parse_command("!deploy")
    assert deploy.args is None
    assert deploy.description == "deploy"


def test_parse_command_invalid() -> None:
    with pytest.raises(OptionBConfigError) as exc:
        parse_command("!invalid", None)
    assert exc.value.code == "OPTB_INVALID_COMMAND"


def test_option_b_service_missing_required_env(monkeypatch) -> None:
    monkeypatch.delenv("AIRTABLE_PAT", raising=False)
    monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
    monkeypatch.delenv("AIRTABLE_BASE_ID", raising=False)
    with pytest.raises(OptionBConfigError) as exc:
        OptionBService.from_env()
    assert exc.value.code == "OPTB_MISSING_AIRTABLE_PAT"
