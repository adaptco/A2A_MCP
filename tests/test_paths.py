import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.prime_directive.util.paths import enforce_allowed_root


def test_enforce_allowed_root_allows_nested_allowed_paths(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    exports = tmp_path / "exports"
    staging.mkdir()
    exports.mkdir()

    monkeypatch.setattr("src.prime_directive.util.paths.ALLOWED_ROOTS", (staging.resolve(), exports.resolve()))

    approved = enforce_allowed_root(staging / "a" / "file.txt")
    assert approved == (staging / "a" / "file.txt").resolve()


def test_enforce_allowed_root_rejects_sibling_prefix(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    sibling = tmp_path / "staging_backup"
    staging.mkdir()
    sibling.mkdir()

    monkeypatch.setattr("src.prime_directive.util.paths.ALLOWED_ROOTS", (staging.resolve(),))

    with pytest.raises(ValueError):
        enforce_allowed_root(sibling / "leak.txt")
