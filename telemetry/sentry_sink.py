"""
telemetry/sentry_sink.py — Gemini OS Telemetry Sentry Sink
===========================================================
Consumes loose artifact vectors from data/vector_lake/, computes geodesic
centroids (cosine-normalized centroid = geometric mean on the unit hypersphere),
and flushes a compacted stateful runtime embedding to Sentry.

Usage (CLI):
    python telemetry/sentry_sink.py \\
        --vector-lake data/vector_lake \\
        --snapshot output/telemetry_snapshot.json

Usage (library):
    from telemetry.sentry_sink import SentrySink
    sink = SentrySink()
    sink.ingest(vectors)
    sink.flush()
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import time
from typing import Any

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [sentry_sink] %(levelname)s %(message)s",
)


# ---------------------------------------------------------------------------
# Geodesic compaction  (no external deps required)
# ---------------------------------------------------------------------------

def _cosine_centroid(vectors: list[list[float]]) -> list[float]:
    """Compute a geodesic centroid: L2-normalized mean of float vectors."""
    if not vectors:
        return []
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for v in vectors:
        for i, val in enumerate(v):
            centroid[i] += val
    n = len(vectors)
    centroid = [c / n for c in centroid]
    norm = sum(c ** 2 for c in centroid) ** 0.5
    if norm > 1e-9:
        centroid = [c / norm for c in centroid]
    return centroid


def _hex_to_vec(fp: str | None, dim: int = 16) -> list[float]:
    if not fp:
        return [0.0] * dim
    return [int(fp[i:i + 2], 16) / 255.0 for i in range(0, min(dim * 2, len(fp)), 2)]


def compact_to_geodesics(snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Compact a vector lake snapshot into a single geodesic centroid embedding.

    The pipeline structure acts as the data embedding layer: each agent run
    produces token-vectors that are geodesically compacted here into a single
    stateful embedding per snapshot (one point on the unit hypersphere per run).
    """
    raw = snapshot.get("vectors", snapshot.get("artifacts", []))

    float_vecs: list[list[float]] = []
    for item in raw:
        if isinstance(item, list):
            float_vecs.append([float(x) for x in item])
        elif isinstance(item, dict):
            if "vector" in item:
                float_vecs.append([float(x) for x in item["vector"]])
            elif "fingerprint" in item:
                float_vecs.append(_hex_to_vec(item["fingerprint"]))

    geodesic = _cosine_centroid(float_vecs)
    return {
        "timestamp": snapshot.get("timestamp"),
        "commit": snapshot.get("commit", "unknown"),
        "vector_count": len(float_vecs),
        "geodesic_centroid": geodesic,
        "geodesic_dim": len(geodesic),
        "stateful_runtime": True,
    }


# ---------------------------------------------------------------------------
# Sentry integration
# ---------------------------------------------------------------------------

class SentrySink:
    """Stateful runtime sink — emits compacted geodesic embeddings to Sentry."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("SENTRY_DSN", "")
        self.environment = os.environ.get("SENTRY_ENVIRONMENT", "production")
        self.release = os.environ.get("SENTRY_RELEASE", "unknown")
        self._ready = False
        self._queue: list[dict] = []

        if self.dsn:
            try:
                import sentry_sdk
                sentry_sdk.init(
                    dsn=self.dsn,
                    environment=self.environment,
                    release=self.release,
                    traces_sample_rate=1.0,
                    enable_tracing=True,
                )
                self._ready = True
                log.info("Sentry initialized (env=%s release=%s)", self.environment, self.release)
            except ImportError:
                log.warning("sentry_sdk not installed — local-only mode")
        else:
            log.warning("SENTRY_DSN not set — local-only mode")

    def ingest(self, payload: dict[str, Any]) -> None:
        self._queue.append(payload)
        log.info(
            "Ingested geodesic: %d-dim centroid over %d vectors",
            payload.get("geodesic_dim", 0),
            payload.get("vector_count", 0),
        )

    def flush(self, snapshot_path: pathlib.Path | None = None) -> None:
        if not self._queue:
            log.info("Nothing to flush")
            return

        combined = {
            "flush_time": time.time(),
            "environment": self.environment,
            "release": self.release,
            "geodesics": self._queue,
        }

        if snapshot_path:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(json.dumps(combined, indent=2))
            log.info("Snapshot written → %s", snapshot_path)

        if self._ready:
            try:
                import sentry_sdk
                with sentry_sdk.start_transaction(
                    op="gemini.telemetry.flush",
                    name="Gemini OS — Vector Geodesic Flush",
                ) as txn:
                    txn.set_tag("vector_count", sum(g.get("vector_count", 0) for g in self._queue))
                    txn.set_tag("geodesic_count", len(self._queue))
                    for g in self._queue:
                        with txn.start_child(op="geodesic.embed", description=g.get("commit", "")):
                            sentry_sdk.set_context("geodesic", g)
                sentry_sdk.flush(timeout=5)
                log.info("Flushed %d geodesics to Sentry", len(self._queue))
            except Exception as exc:  # noqa: BLE001
                log.error("Sentry flush error: %s", exc)
        else:
            log.info("Sentry not configured — %d geodesics in local snapshot only", len(self._queue))

        self._queue.clear()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini OS Sentry Telemetry Sink")
    parser.add_argument("--vector-lake", default="data/vector_lake")
    parser.add_argument("--snapshot", default="output/telemetry_snapshot.json")
    args = parser.parse_args()

    lake = pathlib.Path(args.vector_lake)
    snap_file = lake / "snapshot.json"

    if not snap_file.exists():
        log.warning("No vector snapshot at %s — nothing to flush", snap_file)
        return

    raw = json.loads(snap_file.read_text())
    geodesic = compact_to_geodesics(raw)
    log.info(
        "Compacted %d vectors → %d-dim geodesic centroid",
        geodesic["vector_count"],
        geodesic["geodesic_dim"],
    )

    sink = SentrySink()
    sink.ingest(geodesic)
    sink.flush(snapshot_path=pathlib.Path(args.snapshot))


if __name__ == "__main__":
    main()
