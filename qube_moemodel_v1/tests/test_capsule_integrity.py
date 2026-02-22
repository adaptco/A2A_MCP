"""Dual-root replay validation tests."""

from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "lifecycle" / "capsule_manager.py"

spec = util.spec_from_file_location("capsule_manager", MODULE_PATH)
capsule_manager = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(capsule_manager)  # type: ignore[arg-type]
CapsuleManager = capsule_manager.CapsuleManager


def test_capsule_freeze_roundtrip() -> None:
    manager = CapsuleManager()
    manager.freeze("capsule-alpha")
    assert manager.is_frozen("capsule-alpha")
