import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import psycopg2
from psycopg2.extras import execute_batch


def _load_threads(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _hash_seed(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**31)


def deterministic_embedding(text: str, dim: int = 1536) -> List[float]:
    seed = _hash_seed(text)
    rng = np.random.RandomState(seed)
    vec = rng.rand(dim)
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist()


def upsert_threads(pg_dsn: str, threads: List[Dict], model_id: str) -> None:
    prepared_threads = []
    for thread in threads:
        prepared_threads.append(
            {
                **thread,
                "claims": json.dumps(thread.get("claims", [])),
                "spec_refs": json.dumps(thread.get("spec_refs", [])),
                "tags": json.dumps(thread.get("tags", [])),
            }
        )

    insert_threads_sql = """
        INSERT INTO digital_threads (
            thread_id, corpus_id, project_id, vertical_id, episode_id, type, title, text, source_uri, source_hash,
            claims, spec_refs, tags, sensitivity, created_at, hash
        ) VALUES (
            %(thread_id)s, %(corpus_id)s, %(project_id)s, %(vertical_id)s, %(episode_id)s, %(type)s, %(title)s,
            %(text)s, %(source_uri)s, %(source_hash)s, %(claims)s, %(spec_refs)s, %(tags)s, %(sensitivity)s,
            %(created_at)s, %(hash)s
        )
        ON CONFLICT (thread_id) DO NOTHING;
    """

    insert_embeddings_sql = """
        INSERT INTO thread_embeddings (thread_id, embedding, model_id, metadata)
        VALUES (%(thread_id)s, %(embedding)s, %(model_id)s, %(metadata)s)
        ON CONFLICT (thread_id) DO UPDATE SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata, model_id = EXCLUDED.model_id;
    """

    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor() as cur:
            execute_batch(cur, insert_threads_sql, prepared_threads)
            embedding_rows = []
            for thread in threads:
                embedding_rows.append(
                    {
                        "thread_id": thread["thread_id"],
                        "embedding": deterministic_embedding(thread["text"]),
                        "model_id": model_id,
                        "metadata": json.dumps(
                            {
                                "project_id": thread["project_id"],
                                "vertical_id": thread["vertical_id"],
                                "corpus_id": thread["corpus_id"],
                            }
                        ),
                    }
                )
            execute_batch(cur, insert_embeddings_sql, embedding_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed and upsert digital threads into pgvector")
    parser.add_argument("--pg-dsn", required=True, help="Postgres DSN")
    parser.add_argument("--threads", required=True, help="Path to threads JSONL")
    parser.add_argument("--model-id", default="local.hash.v1", help="Embedding model identifier")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    threads = _load_threads(Path(args.threads))
    upsert_threads(args.pg_dsn, threads, args.model_id)


if __name__ == "__main__":
    main()
