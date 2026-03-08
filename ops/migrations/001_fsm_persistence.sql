CREATE TABLE IF NOT EXISTS fsm_event (
  tenant_id TEXT NOT NULL,
  fsm_id TEXT NOT NULL,
  execution_id TEXT NOT NULL,
  seq BIGINT NOT NULL,
  event_type TEXT NOT NULL,
  event_version INT NOT NULL,
  occurred_at TIMESTAMP NOT NULL,
  payload_canonical BLOB NOT NULL,
  payload_hash BLOB NOT NULL,
  prev_event_hash BLOB NULL,
  event_hash BLOB NOT NULL,
  system_version TEXT NOT NULL,
  hash_version INT NOT NULL,
  certification TEXT NOT NULL,
  PRIMARY KEY (tenant_id, execution_id, seq),
  UNIQUE (tenant_id, execution_id, event_hash)
);

CREATE INDEX IF NOT EXISTS ix_fsm_event_tenant_execution ON fsm_event (tenant_id, execution_id);
CREATE INDEX IF NOT EXISTS ix_fsm_event_tenant_fsm ON fsm_event (tenant_id, fsm_id);

CREATE TABLE IF NOT EXISTS fsm_execution (
  tenant_id TEXT NOT NULL,
  execution_id TEXT PRIMARY KEY,
  fsm_id TEXT NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finalized_at TIMESTAMP NULL,
  head_seq BIGINT NOT NULL DEFAULT 0,
  head_hash BLOB NULL,
  status TEXT NOT NULL,
  policy_hash BLOB NOT NULL,
  role_matrix_ver TEXT NOT NULL,
  materiality_ver TEXT NOT NULL,
  system_version TEXT NOT NULL,
  hash_version INT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fsm_execution_tenant_fsm ON fsm_execution (tenant_id, fsm_id);

CREATE TABLE IF NOT EXISTS fsm_snapshot (
  tenant_id TEXT NOT NULL,
  execution_id TEXT NOT NULL,
  snapshot_seq BIGINT NOT NULL,
  snapshot_canonical BLOB NOT NULL,
  snapshot_hash BLOB NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (tenant_id, execution_id, snapshot_seq)
);
