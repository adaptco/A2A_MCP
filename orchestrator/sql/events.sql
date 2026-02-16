CREATE TABLE IF NOT EXISTS events (
    id BIGINT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    state TEXT NOT NULL,
    payload JSONB NOT NULL,
    hash_prev TEXT,
    hash_current TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_events_one_finalized_per_execution
ON events (tenant_id, execution_id)
WHERE state = 'FINALIZED';
