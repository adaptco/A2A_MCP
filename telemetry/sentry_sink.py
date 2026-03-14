"""
telemetry/sentry_sink.py — Gemini OS Telemetry Sentry Sink
===========================================================
<<<<<<< HEAD
Consumes loose artifact vectors from the data/vector_lake/ data lake,
computes geodesic centroids (cosine-normalized centroid = geometric mean on
the unit hypersphere), and flushes a compacted stateful runtime embedding
to Sentry as a performance transaction + attachment.
=======
Consumes loose artifact vectors from data/vector_lake/, computes geodesic
centroids (cosine-normalized centroid = geometric mean on the unit hypersphere),
and flushes a compacted stateful runtime embedding to Sentry.
>>>>>>> origin/main

Usage (CLI):
    python telemetry/sentry_sink.py \\
        --vector-lake data/vector_lake \\
        --snapshot output/telemetry_snapshot.json

<<<<<<< HEAD
Usage (as library):
=======
Usage (library):
>>>>>>> origin/main
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
<<<<<<< HEAD
logging.basicConfig(level=logging.INFO, format="%(asctime)s [sentry_sink] %(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Geodesic compaction
# ---------------------------------------------------------------------------

def _cosine_centroid(vectors: list[list[float]]) -> list[float]:
    """Compute a geodesic centroid (L2-normalized mean) of float vectors."""
=======
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [sentry_sink] %(levelname)s %(message)s",
)


# ---------------------------------------------------------------------------
# Geodesic compaction  (no external deps required)
# ---------------------------------------------------------------------------

def _cosine_centroid(vectors: list[list[float]]) -> list[float]:
    """Compute a geodesic centroid: L2-normalized mean of float vectors."""
>>>>>>> origin/main
    if not vectors:
        return []
    dim = len(vectors[0])
    centroid = [0.0] * dim
    for v in vectors:
        for i, val in enumerate(v):
            centroid[i] += val
    n = len(vectors)
    centroid = [c / n for c in centroid]
<<<<<<< HEAD
    # L2 normalize → project onto unit hypersphere (geodesic centroid)
=======
>>>>>>> origin/main
    norm = sum(c ** 2 for c in centroid) ** 0.5
    if norm > 1e-9:
        centroid = [c / norm for c in centroid]
    return centroid


<<<<<<< HEAD
def compact_to_geodesics(snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Consume a vector lake snapshot and compact vectors into geodesic tokens.
    The pipeline structure becomes the data embedding layer — each agent run
    produces float-vector tokens that are compacted here into a single
    stateful embedding geodesic per artifact group.
    """
    raw_vectors: list[Any] = snapshot.get("vectors", [])
    artifacts: list[Any] = snapshot.get("artifacts", [])

    # If vectors are plain fingerprint dicts (fallback mode), encode as unit vectors
    if raw_vectors and isinstance(raw_vectors[0], dict):
        # Encode fingerprint hex into a simple float vector (dim=16)
        def _hex_to_vec(fp: str | None) -> list[float]:
            if not fp:
                return [0.0] * 16
            return [int(fp[i:i+2], 16) / 255.0 for i in range(0, min(32, len(fp)), 2)]

        raw_vectors = [_hex_to_vec(v.get("fingerprint")) for v in raw_vectors]
    elif artifacts and not raw_vectors:
        def _hex_to_vec(fp: str | None) -> list[float]:
            if not fp:
                return [0.0] * 16
            return [int(fp[i:i+2], 16) / 255.0 for i in range(0, min(32, len(fp)), 2)]
        raw_vectors = [_hex_to_vec(a.get("fingerprint")) for a in artifacts]

    geodesic = _cosine_centroid(raw_vectors)
    return {
        "timestamp": snapshot.get("timestamp"),
        "commit": snapshot.get("commit", "unknown"),
        "vector_count": len(raw_vectors),
=======
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
>>>>>>> origin/main
        "geodesic_centroid": geodesic,
        "geodesic_dim": len(geodesic),
        "stateful_runtime": True,
    }


# ---------------------------------------------------------------------------
# Sentry integration
# ---------------------------------------------------------------------------

class SentrySink:
<<<<<<< HEAD
    """
    Stateful runtime sink — emits compacted geodesic embeddings to Sentry.

    The Sentry envelope acts as the artifact store for the embedded token
    manifold, consumed by the MCP HTTP control layer (mcp_servers/gemini_control.py).
    """

    def __init__(self, dsn: str | None = None, environment: str = "production") -> None:
        self.dsn = dsn or os.environ.get("SENTRY_DSN", "")
        self.environment = os.environ.get("SENTRY_ENVIRONMENT", environment)
        self.release = os.environ.get("SENTRY_RELEASE", "unknown")
        self._sentry_ready = False
        self._geodesics: list[dict] = []
=======
    """Stateful runtime sink — emits compacted geodesic embeddings to Sentry."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("SENTRY_DSN", "")
        self.environment = os.environ.get("SENTRY_ENVIRONMENT", "production")
        self.release = os.environ.get("SENTRY_RELEASE", "unknown")
        self._ready = False
        self._queue: list[dict] = []
>>>>>>> origin/main

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
<<<<<<< HEAD
                self._sentry_ready = True
                log.info("Sentry SDK initialized (env=%s release=%s)", self.environment, self.release)
            except ImportError:
                log.warning("sentry_sdk not installed — telemetry will be local-only")
        else:
            log.warning("SENTRY_DSN not set — running in local-only mode")

    def ingest(self, geodesic_payload: dict[str, Any]) -> None:
        """Receive a compacted geodesic payload for eventual flush."""
        self._geodesics.append(geodesic_payload)
        log.info(
            "Ingested geodesic: %d-dim centroid over %d vectors",
            geodesic_payload.get("geodesic_dim", 0),
            geodesic_payload.get("vector_count", 0),
        )

    def flush(self, snapshot_path: pathlib.Path | None = None) -> None:
        """Flush all geodesics to Sentry (and optionally write a local snapshot)."""
        if not self._geodesics:
            log.info("No geodesics to flush")
=======
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
>>>>>>> origin/main
            return

        combined = {
            "flush_time": time.time(),
            "environment": self.environment,
            "release": self.release,
<<<<<<< HEAD
            "geodesics": self._geodesics,
        }

        # Write local snapshot regardless of Sentry status
        if snapshot_path:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(json.dumps(combined, indent=2))
            log.info("Telemetry snapshot written → %s", snapshot_path)

        if self._sentry_ready:
=======
            "geodesics": self._queue,
        }

        if snapshot_path:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(json.dumps(combined, indent=2))
            log.info("Snapshot written → %s", snapshot_path)

        if self._ready:
>>>>>>> origin/main
            try:
                import sentry_sdk
                with sentry_sdk.start_transaction(
                    op="gemini.telemetry.flush",
                    name="Gemini OS — Vector Geodesic Flush",
                ) as txn:
<<<<<<< HEAD
                    txn.set_tag("vector_count", sum(g.get("vector_count", 0) for g in self._geodesics))
                    txn.set_tag("geodesic_count", len(self._geodesics))

                    for g in self._geodesics:
                        with txn.start_child(op="geodesic.embed", description=g.get("commit", "unknown")):
                            sentry_sdk.set_context("geodesic", g)

                sentry_sdk.flush(timeout=5)
                log.info("Flushed %d geodesics to Sentry", len(self._geodesics))
            except Exception as exc:  # noqa: BLE001
                log.error("Sentry flush error: %s", exc)
        else:
            log.info("Sentry not configured — %d geodesics written to local snapshot only", len(self._geodesics))

        self._geodesics.clear()


# ---------------------------------------------------------------------------
# CLI entrypoint
=======
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
>>>>>>> origin/main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini OS Sentry Telemetry Sink")
<<<<<<< HEAD
    parser.add_argument("--vector-lake", default="data/vector_lake", help="Path to vector lake directory")
    parser.add_argument("--snapshot", default="output/telemetry_snapshot.json", help="Output snapshot path")
    args = parser.parse_args()

    lake = pathlib.Path(args.vector_lake)
    snapshot_file = lake / "snapshot.json"

    if not snapshot_file.exists():
        log.warning("No vector snapshot found at %s — nothing to flush", snapshot_file)
        return

    raw = json.loads(snapshot_file.read_text())
    geodesic = compact_to_geodesics(raw)
    log.info("Compacted %d vectors → %d-dim geodesic centroid", geodesic["vector_count"], geodesic["geodesic_dim"])
=======
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
>>>>>>> origin/main

    sink = SentrySink()
    sink.ingest(geodesic)
    sink.flush(snapshot_path=pathlib.Path(args.snapshot))


if __name__ == "__main__":
    main()
