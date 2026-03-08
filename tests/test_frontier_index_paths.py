from pathlib import Path

from scripts.build_frontier_agent_index import _normalize_token_ref


def test_token_ref_is_relative_when_path_is_under_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    token_path = repo / "runtime" / "rbac" / "tokens.json"
    assert _normalize_token_ref(token_path, repo) == "runtime/rbac/tokens.json"


def test_token_ref_keeps_absolute_path_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "tokens.json"
    assert _normalize_token_ref(outside, repo).endswith("tokens.json")
