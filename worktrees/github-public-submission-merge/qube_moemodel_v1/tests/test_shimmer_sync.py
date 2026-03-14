"""Timestamp fidelity across nodes."""

from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "hud" / "shimmer_renderer.py"

spec = util.spec_from_file_location("shimmer_renderer", MODULE_PATH)
shimmer_renderer = util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(shimmer_renderer)  # type: ignore[arg-type]
ShimmerRenderer = shimmer_renderer.ShimmerRenderer


def test_renderer_formats_timestamp() -> None:
    renderer = ShimmerRenderer()
    rendered = renderer.render({"timestamp": 123.456, "emotional_hue": 0.42})
    assert "123.456" in rendered
    assert "0.42" in rendered
