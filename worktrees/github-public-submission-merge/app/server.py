from __future__ import annotations

import json
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from codex_qernel import CodexQernel, QernelConfig
# Mock MergeModel if not available or find where it is defined
try:
    from qube_moemodel_v1 import MergeModel
except ImportError:
    class MergeModel:
        @staticmethod
        def from_file(path: Path) -> MergeModel:
            return MergeModel()
        @staticmethod
        def empty() -> MergeModel:
            return MergeModel()
        @property
        def version(self) -> str:
            return "0.0.0"

logger = logging.getLogger("core_orchestrator.server")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
SCROLLSTREAM_LEDGER = BASE_DIR / "data" / "scrollstream" / "scrollstream_ledger.ndjson"
CONTENT_TYPE_JSON = "application/json"

CONFIG = QernelConfig.from_env(base_dir=BASE_DIR)
_QERNEL: CodexQernel | None = None
_QERNEL_ERROR: str | None = None
<<<<<<< HEAD

=======
>>>>>>> origin/main

def _default_static_root() -> Path:
    configured = os.environ.get("PORTAL_STATIC_ROOT")
    if configured:
        return Path(configured)
    return BASE_DIR / "public"


def _default_portal_entrypoint(static_root: Path) -> Path:
    configured = os.environ.get("PORTAL_ENTRYPOINT")
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            candidate = static_root / candidate
        return candidate
    return static_root / "hud" / "capsules" / "avatar" / "index.html"

STATIC_ROOT = _default_static_root().resolve()
PORTAL_ENTRYPOINT = _default_portal_entrypoint(STATIC_ROOT).resolve()

try:
    PORTAL_ENTRYPOINT.relative_to(STATIC_ROOT)
except ValueError:  # pragma: no cover - configuration safeguard
    logger.warning(
        "Portal entrypoint %s is not within static root %s; falling back to default",
        PORTAL_ENTRYPOINT,
        STATIC_ROOT,
    )
    PORTAL_ENTRYPOINT = (STATIC_ROOT / "hud" / "capsules" / "avatar" / "index.html").resolve()

if not PORTAL_ENTRYPOINT.exists():  # pragma: no cover - startup diagnostics
    logger.warning("Portal entrypoint %s does not exist", PORTAL_ENTRYPOINT)

mimetypes.add_type("application/json", ".json")


def _load_scrollstream_events() -> list[dict[str, Any]]:
    if not SCROLLSTREAM_LEDGER.exists():
        return []

    events: list[dict[str, Any]] = []
    with SCROLLSTREAM_LEDGER.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed scrollstream line")
    return events


def resolve_portal_asset(request_path: str) -> Path | None:
    normalized = request_path or "/"
    if normalized == "/":
        candidate = PORTAL_ENTRYPOINT
    else:
        relative = normalized.lstrip("/")
        candidate = STATIC_ROOT / relative

    # Resolve the candidate once and ensure it stays within STATIC_ROOT
    try:
        resolved = candidate.resolve()
        resolved.relative_to(STATIC_ROOT)
    except ValueError:
        return None

    if resolved.is_dir():
        resolved = (resolved / "index.html").resolve()
        try:
            resolved.relative_to(STATIC_ROOT)
        except ValueError:
            return None

class RequestHandler(BaseHTTPRequestHandler):
    """HTTP interface exposing portal assets and CODEX qernel primitives."""

    server_version = "CoreOrchestratorHTTP/2.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/health":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"status": "degraded", "error": _QERNEL_ERROR or "qernel_unavailable"})
                return
            self._send_json(200, qernel.health_status())
            return

        if path == "/scrollstream/rehearsal":
            payload = {
                "capsule": "capsule.rehearsal.scrollstream.v1",
                "ledger": "scrollstream_ledger",
                "events": _load_scrollstream_events(),
            }
            self._send_response(200, payload)
            return

        if path == "/capsules":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            params = parse_qs(parsed.query)
            refresh_requested = params.get("refresh", ["0"])[0].lower() in {"1", "true", "yes"}
            if refresh_requested:
                qernel.refresh()
            self._send_json(200, {"capsules": qernel.list_capsules()})
            return

        if path.startswith("/capsules/"):
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            capsule_id = path.split("/", 2)[2]
            manifest = qernel.get_capsule(capsule_id)
            if manifest is None:
                self._send_json(404, {"error": "capsule_not_found", "capsule_id": capsule_id})
                return
            self._send_json(200, manifest)
            return

        if path == "/events":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            events = [event.__dict__ for event in qernel.read_events(limit=50)]
            self._send_json(200, {"events": events})
            return
        if path == "/scrollstream/ledger":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            params = parse_qs(parsed.query)
            try:
                limit = int(params.get("limit", ["10"])[0])
            except ValueError:
                self._send_json(400, {"error": "invalid_limit"})
                return
            ledger = qernel.read_scrollstream_ledger(limit=max(1, min(limit, 100)))
            self._send_json(200, {"entries": ledger})
<<<<<<< HEAD
            return
        if path == "/scrollstream/rehearsal":
            self._send_json(
                200,
                {
                    "capsule": "capsule.rehearsal.scrollstream.v1",
                    "ledger": "scrollstream_ledger",
                    "events": _load_scrollstream_events(),
                },
            )
            return

        asset = resolve_portal_asset(parsed.path)
        if asset is not None:
            self._send_asset(asset)
            return
        self._send_json(404, {"error": "not_found", "path": parsed.path})
=======
            return
        if path == "/scrollstream/rehearsal":
            self._send_json(
                200,
                {
                    "capsule": "capsule.rehearsal.scrollstream.v1",
                    "ledger": "scrollstream_ledger",
                    "events": _load_scrollstream_events(),
                },
            )
            return
>>>>>>> origin/main

        asset = resolve_portal_asset(parsed.path)
        if asset is not None:
            self._send_asset(asset)
            return
        self._send_json(404, {"error": "not_found", "path": parsed.path})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/capsules/refresh":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            qernel.refresh()
            self._send_json(200, {"status": "refreshed", "capsule_count": len(qernel.list_capsules())})
            return

        if path == "/events":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            payload = self._load_json_body()
            if not isinstance(payload, dict):
                self._send_json(400, {"error": "invalid_payload"})
                return
            event_name = str(payload.get("event", "")).strip()
            event_payload = payload.get("payload", {})
            if not event_name:
                self._send_json(400, {"error": "missing_event_name"})
                return
            if not isinstance(event_payload, dict):
                self._send_json(400, {"error": "payload_must_be_object"})
                return
            event = qernel.record_event(event_name, event_payload)
            self._send_json(201, event.__dict__)
            return

        if path == "/scrollstream/rehearsal":
            qernel = _get_qernel()
            if qernel is None:
                self._send_json(503, {"error": "qernel_unavailable", "detail": _QERNEL_ERROR})
                return
            payload = self._load_json_body() or {}
            training_mode = bool(payload.get("training_mode", True)) if isinstance(payload, dict) else True
            entries = qernel.emit_scrollstream_rehearsal(training_mode=training_mode)
            self._send_json(201, {"entries": entries})
            return
<<<<<<< HEAD

        self._send_json(404, {"error": "not_found", "path": parsed.path})
=======
>>>>>>> origin/main

        self._send_json(404, {"error": "not_found", "path": parsed.path})

<<<<<<< HEAD
=======
    def _serve_static(self, path: Path) -> None:
        self.send_response(200)
        ctype, _ = mimetypes.guess_type(str(path))
        self.send_header("Content-Type", ctype or "application/octet-stream")
        stat = path.stat()
        self.send_header("Content-Length", str(stat.st_size))
        self.end_headers()
        with path.open("rb") as f:
            self.wfile.write(f.read())

>>>>>>> origin/main
    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_asset(self, asset: Path) -> None:
        body = asset.read_bytes()
        content_type = mimetypes.guess_type(str(asset))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load_json_body(self) -> Any:
        content_length = self.headers.get("Content-Length")
        if not content_length: return None
        try:
            length = int(content_length)
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return None

def main() -> None:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer((host, port), RequestHandler)
    logger.info("Starting CODEX qernel HTTP server on %s:%s (capsules_dir=%s)", host, port, CONFIG.capsules_dir)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()


def _get_qernel() -> CodexQernel | None:
    global _QERNEL, _QERNEL_ERROR
    if _QERNEL is not None:
        return _QERNEL
    if _QERNEL_ERROR is not None:
        return None
    try:
        _QERNEL = CodexQernel(CONFIG)
    except Exception as exc:  # pragma: no cover - defensive
        _QERNEL_ERROR = str(exc)
        logger.exception("Failed to initialize CodexQernel")
        return None
    return _QERNEL
