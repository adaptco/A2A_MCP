from __future__ import annotations

import importlib
import io
import json
import sys
import tempfile
import tomllib
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import yaml

from codex_qernel.capsules import CapsuleManifest


def test_capsule_manifest_rejects_non_object_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "array.json"
        manifest_path.write_text("[]", encoding="utf-8")

        try:
            CapsuleManifest.from_path(manifest_path)
        except ValueError as exc:
            assert "JSON object" in str(exc)
        else:  # pragma: no cover - explicit failure path
            raise AssertionError("Expected ValueError for non-object manifest payload")


def test_app_server_import_does_not_raise_name_error() -> None:
    module = importlib.import_module("app.server")
    assert hasattr(module, "MERGE_MODEL")


class _DummyHandler:
    def __init__(self) -> None:
        self.status_codes: list[int] = []
        self.headers: list[tuple[str, str]] = []
        self.wfile = io.BytesIO()
        self.ended = False

    def send_response(self, status_code: int) -> None:
        self.status_codes.append(status_code)

    def send_header(self, key: str, value: str) -> None:
        self.headers.append((key, value))

    def end_headers(self) -> None:
        self.ended = True


def test_send_response_uses_defined_json_content_type() -> None:
    module = importlib.import_module("app.server")
    dummy = _DummyHandler()

    module.RequestHandler._send_response(dummy, 200, {"status": "ok"})

    assert dummy.status_codes == [200]
    assert ("Content-Type", module.CONTENT_TYPE_JSON) in dummy.headers
    assert dummy.ended is True
    assert json.loads(dummy.wfile.getvalue().decode("utf-8")) == {"status": "ok"}


def test_artifact_workflow_yaml_is_valid() -> None:
    workflow = Path(".github/workflows/art.i.fact.yml")
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))

    assert isinstance(document, dict)
    assert "jobs" in document


def test_dev_dependencies_include_pyyaml() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dev_deps = pyproject["project"]["optional-dependencies"]["dev"]

    assert any(dep.lower().startswith("pyyaml") for dep in dev_deps)


def test_verify_hero_app_re_raises_playwright_failures() -> None:
    fake_sync_api = ModuleType("playwright.sync_api")
    fake_sync_api.sync_playwright = Mock()
    fake_playwright = ModuleType("playwright")
    fake_playwright.sync_api = fake_sync_api
    sys.modules["playwright"] = fake_playwright
    sys.modules["playwright.sync_api"] = fake_sync_api

    module = importlib.import_module("verify_hero_app")
    page = Mock()
    page.goto.side_effect = RuntimeError("navigation timed out")
    browser = Mock()
    browser.new_page.return_value = page
    chromium = Mock()
    chromium.launch.return_value = browser

    try:
        module.run(SimpleNamespace(chromium=chromium))
    except RuntimeError as exc:
        assert "navigation timed out" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Expected verify_hero_app.run to re-raise failures")

    page.screenshot.assert_called_with(path="error_state.png")
    browser.close.assert_called_once()
