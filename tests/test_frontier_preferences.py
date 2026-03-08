from pathlib import Path

from scripts import frontier_preferences


def test_load_workspace_preferences_reads_existing_anchors(tmp_path: Path, monkeypatch) -> None:
    agents = tmp_path / "AGENTS.md"
    skills = tmp_path / "Skills.md"
    agents.write_text("a\nb\n", encoding="utf-8")
    skills.write_text("skill\n", encoding="utf-8")

    monkeypatch.setattr(frontier_preferences, "DEFAULT_MEMORY_ANCHORS", [agents, skills])

    prefs = frontier_preferences.load_workspace_preferences()

    assert prefs["memory_anchor_count"] == 2
    assert prefs["memory_anchors"][0]["line_count"] == "2"
