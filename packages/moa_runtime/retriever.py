from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

from .contracts import deterministic_embedding
from .types import ContextBundle, RetrievedChunk


def _format_vector(values: List[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def retrieve(
    pg_dsn: str,
    manifest: Dict[str, Any],
    query: str,
    top_k: int,
    min_score: float,
) -> ContextBundle:
    query_embedding = manifest.get("query_embedding")
    if not query_embedding:
        query_embedding = deterministic_embedding(query)
    vector_literal = _format_vector(query_embedding)
    sql = """
        SELECT
            dt.thread_id,
            dt.text,
            dt.source_uri,
            dt.source_hash,
            te.embedding <=> %s AS score,
            COALESCE(te.metadata, '{}'::jsonb) AS metadata
        FROM digital_threads dt
        JOIN thread_embeddings te ON dt.thread_id = te.thread_id
        WHERE (%s IS NULL OR dt.project_id = %s)
          AND (%s IS NULL OR dt.vertical_id = %s)
        ORDER BY te.embedding <=> %s ASC
        LIMIT %s
    """
    project_id = manifest.get("project_id")
    vertical_id = manifest.get("vertical_id")
    params = (
        vector_literal,
        project_id,
        project_id,
        vertical_id,
        vertical_id,
        vector_literal,
        top_k,
    )

    with psycopg2.connect(pg_dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows: List[Dict[str, Any]] = cur.fetchall()

    chunks = []
    for row in rows:
        score = float(row["score"])
        if min_score is not None and score > min_score:
            continue
        chunks.append(
            RetrievedChunk(
                thread_id=row["thread_id"],
                content=row["text"],
                score=score,
                metadata={
                    "source_uri": row.get("source_uri"),
                    "source_hash": row.get("source_hash"),
                    **(row.get("metadata") or {}),
                },
            )
        )
    return ContextBundle(chunks=chunks)
