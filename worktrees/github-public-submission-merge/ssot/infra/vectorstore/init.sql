CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS digital_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT UNIQUE NOT NULL,
    corpus_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    vertical_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT,
    text TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    claims JSONB DEFAULT '[]'::jsonb,
    spec_refs JSONB DEFAULT '[]'::jsonb,
    tags JSONB DEFAULT '[]'::jsonb,
    sensitivity TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thread_embeddings (
    thread_id TEXT UNIQUE NOT NULL REFERENCES digital_threads(thread_id),
    embedding vector(1536) NOT NULL,
    model_id TEXT DEFAULT 'local.hash.v1',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create ANN index when supported by pgvector; IVFFlat for cosine.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'thread_embeddings_ivfflat'
    ) THEN
        BEGIN
            EXECUTE 'CREATE INDEX thread_embeddings_ivfflat ON thread_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);';
        EXCEPTION
            WHEN others THEN
                -- Fallback: create a plain index if IVFFlat unavailable (e.g., during tests).
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'thread_embeddings_cosine'
                ) THEN
                    EXECUTE 'CREATE INDEX thread_embeddings_cosine ON thread_embeddings USING gist (embedding vector_cosine_ops);';
                END IF;
        END;
    END IF;
END
$$;
