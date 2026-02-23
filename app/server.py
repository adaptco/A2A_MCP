import os
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.merge_model import MergeModel

def _default_model_path() -> str:
    return os.getenv("MERGE_MODEL_PATH", "model.json")

try:
    MERGE_MODEL = MergeModel.from_file(_default_model_path())
except Exception:
    MERGE_MODEL = MergeModel.empty()

def resolve_portal_asset(request_path: str) -> Optional[Path]:
    return Path(request_path)

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content_type, _ = mimetypes.guess_type(self.path)
        if content_type is None:
            content_type = "application/octet-stream"
        self.send_header("Content-Type", content_type)
        pass
