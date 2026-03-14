"""Spark Test pass/fail scenarios for overlay enforcement."""

from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "experts" / "overlay_expert.py"

spec = util.spec_from_file_location("overlay_expert", MODULE_PATH)
overlay_expert = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(overlay_expert)  # type: ignore[arg-type]
OverlayExpert = overlay_expert.OverlayExpert


def test_overlay_accepts_matching_persona() -> None:
    expert = OverlayExpert(persona="CiCi")
    assert expert.validate({"persona": "CiCi"})


def test_overlay_rejects_mismatch() -> None:
    expert = OverlayExpert(persona="CiCi")
    assert not expert.validate({"persona": "AltPersona"})
