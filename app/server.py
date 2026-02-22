from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from codex_qernel import CodexQernel, QernelConfig

logger = logging.getLogger("core_orchestrator.server")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
SCROLLSTREAM_LEDGER = BASE_DIR / "data" / "scrollstream" / "scrollstream_ledger.ndjson"


def _load_scrollstream_events() -> list[dict]:
    if not SCROLLSTREAM_LEDGER.exists():
        return []

    events: list[dict] = []
    with SCROLLSTREAM_LEDGER.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed scrollstream line", extra={"line": line})
    return events


class RequestHandler(BaseHTTPRequestHandler):
    """Serve a minimal health endpoint for smoke tests."""

    server_version = "CoreOrchestratorHTTP/1.0"

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        """Respond to GET requests with a JSON health payload."""

        path = self.path.rstrip("/")

        if path == "/health":
            payload = {"status": "ok"}
            body = json.dumps(payload).encode("utf-8")
            self._send_response(200, body)
            logger.info("Responded to /health request")
        elif path == "/scrollstream/rehearsal":
            payload = {
                "capsule": "capsule.rehearsal.scrollstream.v1",
                "ledger": "scrollstream_ledger",
                "events": _load_scrollstream_events(),
            }
            body = json.dumps(payload).encode("utf-8")
            self._send_response(200, body)
            logger.info("Served rehearsal scrollstream payload with %s events", len(payload["events"]))
        else:
            self._send_response(404, b"{}")
            logger.warning("Unhandled path requested: %s", self.path)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        """Silence the default stdout logging to keep CI logs tidy."""

        logger.debug("Request: " + format, *args)

    def _send_response(self, status_code: int, body: bytes) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
CONFIG = QernelConfig.from_env(base_dir=BASE_DIR)
QERNEL = CodexQernel(CONFIG)


def _default_model_path() -> Path:
    """Resolve the merge model path from environment or repository defaults."""

    configured = os.environ.get("MERGE_MODEL_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "specs" / "branch-merge-model.v1.json"


try:
    MERGE_MODEL = MergeModel.from_file(_default_model_path())
    logger.info("Loaded merge model with version %s", MERGE_MODEL.version)
except (FileNotFoundError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
    logger.error("Unable to load merge model: %s", exc)
    MERGE_MODEL = MergeModel.empty()


def _default_static_root() -> Path:
    """Resolve the static asset root from environment or repo defaults."""

    configured = os.environ.get("PORTAL_STATIC_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "public"


def _default_portal_entrypoint(static_root: Path) -> Path:
    """Resolve the entrypoint HTML for the portal experience."""

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
        "Portal entrypoint %s is not within the static root %s; falling back to default",
        PORTAL_ENTRYPOINT,
        STATIC_ROOT,
    )
    PORTAL_ENTRYPOINT = (STATIC_ROOT / "hud" / "capsules" / "avatar" / "index.html").resolve()

if not PORTAL_ENTRYPOINT.exists():  # pragma: no cover - startup diagnostics
    logger.warning("Portal entrypoint %s does not exist", PORTAL_ENTRYPOINT)

mimetypes.add_type("application/json", ".json")


def resolve_portal_asset(request_path: str) -> Optional[Path]:
    """Map an HTTP request path to an on-disk portal asset if available."""

    normalized = request_path or "/"
    if normalized == "/":
        candidate = PORTAL_ENTRYPOINT
    else:
        relative = normalized.lstrip("/")
        candidate = (STATIC_ROOT / relative).resolve()
        if candidate.is_dir():
            candidate = (candidate / "index.html").resolve()

    try:
        candidate.relative_to(STATIC_ROOT)
    except ValueError:
        return None

    if candidate.is_file():
        return candidate
    return None


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP interface exposing the CODEX qernel primitives."""

    server_version = "CoreOrchestratorHTTP/2.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/health":
            self._send_response(200, QERNEL.health_status())
            logger.info("Health probe served")
            return
        if path == "/capsules":
            params = parse_qs(parsed.query)
            refresh_requested = params.get("refresh", ["0"])[0].lower() in {"1", "true", "yes"}
            if refresh_requested:
                QERNEL.refresh()
                logger.info("Capsule catalog refreshed via query parameter")
            capsules = QERNEL.list_capsules()
            self._send_response(200, {"capsules": capsules})
            return
        if path.startswith("/capsules/"):
            capsule_id = path.split("/", 2)[2]
            manifest = QERNEL.get_capsule(capsule_id)
            if manifest is None:
                self._send_response(404, {"error": "capsule_not_found", "capsule_id": capsule_id})
                return
            self._send_response(200, manifest)
            return
        if path == "/events":
            events = [event.__dict__ for event in QERNEL.read_events(limit=50)]
            self._send_response(200, {"events": events})
            return
        if path == "/scrollstream/ledger":
            params = parse_qs(parsed.query)
            try:
                limit = int(params.get("limit", ["10"])[0])
            except ValueError:
                self._send_response(400, {"error": "invalid_limit"})
                return
            ledger = QERNEL.read_scrollstream_ledger(limit=max(1, min(limit, 100)))
            self._send_response(200, {"entries": ledger})
            return
        self._send_response(404, {"error": "not_found", "path": parsed.path})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/capsules/refresh":
            QERNEL.refresh()
            self._send_response(200, {"status": "refreshed", "capsule_count": len(QERNEL.list_capsules())})
            logger.info("Capsule catalog refreshed via POST")
            return
        if path == "/events":
            payload = self._load_json_body()
            if not isinstance(payload, dict):
                self._send_response(400, {"error": "invalid_payload"})
                return
            event_name = str(payload.get("event", "")).strip()
            event_payload = payload.get("payload", {})
            if not event_name:
                self._send_response(400, {"error": "missing_event_name"})
                return
            if not isinstance(event_payload, dict):
                self._send_response(400, {"error": "payload_must_be_object"})
                return
            event = QERNEL.record_event(event_name, event_payload)
            self._send_response(201, event.__dict__)
            logger.info("Recorded event %s", event_name)
            return
        if path == "/scrollstream/rehearsal":
            payload = self._load_json_body() or {}
            training_mode = True
            if isinstance(payload, dict):
                training_mode = bool(payload.get("training_mode", True))
            entries = QERNEL.emit_scrollstream_rehearsal(training_mode=training_mode)
            self._send_response(201, {"entries": entries})
            logger.info("Scrollstream rehearsal emitted (training_mode=%s)", training_mode)
            return
        self._send_response(404, {"error": "not_found", "path": parsed.path})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        logger.debug("Request: " + format, *args)

    # Helpers -------------------------------------------------------------
    def _send_response(self, status_code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load_json_body(self) -> Any:
        content_length = self.headers.get("Content-Length")
        if not content_length:
            return None
        try:
            length = int(content_length)
        except ValueError:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None


def main() -> None:
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer((host, port), RequestHandler)
    logger.info("Starting Core Orchestrator HTTP server on %s:%s", host, port)
    logger.info(
        "Starting CODEX qernel HTTP server on %s:%s (capsules_dir=%s)",
        host,
        port,
        CONFIG.capsules_dir,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down HTTP server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
