import argparse
import hashlib
import sys
from typing import Any, Dict, List

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor


def _deterministic_embedding(text: str, dim: int = 1536) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    seed = int(digest[:16], 16) % (2**31)
    rng = np.random.RandomState(seed)
    vec = rng.rand(dim)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist()


def _fetch_sample(cur) -> Dict[str, Any]:
    cur.execute(
        """
        SELECT dt.thread_id, te.embedding
        FROM digital_threads dt
        JOIN thread_embeddings te ON dt.thread_id = te.thread_id
        ORDER BY random()
        LIMIT 1
        """
    )
    return cur.fetchone()


def _check_retrieval(cur, query_embedding, min_score: float, expect_min: int) -> bool:
    cur.execute(
        """
        SELECT dt.thread_id, te.embedding <=> %s AS score
        FROM digital_threads dt
        JOIN thread_embeddings te ON dt.thread_id = te.thread_id
        ORDER BY te.embedding <=> %s ASC
        LIMIT %s
        """,
        (query_embedding, query_embedding, expect_min),
    )
    rows = cur.fetchall()
    if len(rows) < expect_min:
        return False
    return any(float(row["score"]) <= min_score for row in rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve a sample thread to validate index wiring")
    parser.add_argument("--pg-dsn", required=True, help="Postgres DSN")
    parser.add_argument("--query", required=True, help="Query text")
    parser.add_argument("--expect-min", type=int, default=3, help="Minimum rows expected")
    parser.add_argument("--min-score", type=float, default=0.25, help="Minimum acceptable similarity score")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    query_embedding = _deterministic_embedding(args.query)
    with psycopg2.connect(args.pg_dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sample = _fetch_sample(cur)
            if not sample:
                print("No threads available for retrieval smoke test.", file=sys.stderr)
                return 1
            ok = _check_retrieval(cur, query_embedding, args.min_score, args.expect_min)
            if not ok:
                print("Retrieval did not meet expectations.", file=sys.stderr)
                return 1
    print("Retrieval smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
