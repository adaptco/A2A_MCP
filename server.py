"""Deterministic embedding server for ZERO-DRIFT verification.

This lightweight HTTP server exposes a single `/v1/embeddings` endpoint that
returns a deterministic Top-K ranking. It uses Kahan summation for score
stability and a tie-breaker on `(score, doc_id)` to guarantee consistent order
across architectures.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_EVEN
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List

DOCS = [
    {"doc_id": 1, "vector": [0.1, 0.2]},
    {"doc_id": 2, "vector": [0.1000001, 0.2]},
    {"doc_id": 3, "vector": [0.05, 0.05, 0.05]},
]


def normalize_text(text: str) -> str:
    """Lowercase, trim, and collapse internal whitespace for canonical form."""
    return " ".join(text.strip().lower().split())


def kahan_sum(values: List[float]) -> float:
    """Compute a numerically stable sum using Kahan summation."""
    total = 0.0
    compensation = 0.0
    for value in values:
        y = value - compensation
        t = total + y
        compensation = (t - total) - y
        total = t
    return total


def quantize_score(value: float, precision: int = 6) -> float:
    """Round a score to a fixed precision using Decimal for determinism."""

    quantum = Decimal("1").scaleb(-precision)
    quantized = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_EVEN)
    return float(quantized)


def rank_documents() -> list[dict]:
    """Return documents ordered by stable score and doc id tie-breakers."""

    scored: list[dict] = []
    for doc in DOCS:
        raw_score = kahan_sum(doc["vector"])
        score = quantize_score(raw_score)
        scored.append({"doc_id": doc["doc_id"], "score": score})

    scored.sort(key=lambda x: (-x["score"], x["doc_id"]))
    return scored


class Handler(BaseHTTPRequestHandler):
    """HTTP handler exposing the deterministic embedding ranking."""

    server_version = "ZeroDriftEmbedding/1.0"

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/embeddings":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        raw_input = payload.get("input", "")
        canonical = normalize_text(raw_input)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        ranking = rank_documents()

        response = {
            "object": "list",
            "canonical_input": canonical,
            "hash": digest,
            "ids": [entry["doc_id"] for entry in ranking],
            "scores": ranking,
        }

        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Embedding server listening on http://0.0.0.0:8000")
    server.serve_forever()
