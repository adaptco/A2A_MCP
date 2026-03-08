-- Agent Control Schema v1.0
-- Adds action registry, workflow runs, steps, approvals, event log, and immutable step artifacts.

CREATE TABLE IF NOT EXISTS actions (
    action_id VARCHAR(255) PRIMARY KEY,
    namespace VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL,
    input_schema JSONB NOT NULL,
    output_schema JSONB NOT NULL,
    auth_config JSONB NOT NULL,
    policy_config JSONB NOT NULL,
    execution_config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(namespace, name, version)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    dag_spec JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS steps (
    step_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(run_id),
    node_id VARCHAR(100) NOT NULL,
    action_id VARCHAR(255) REFERENCES actions(action_id),
    inputs JSONB,
    outputs JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    attempt_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(run_id, node_id)
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID REFERENCES steps(step_id),
    policy_name VARCHAR(100) NOT NULL,
    approver_group VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    approver_id VARCHAR(255),
    decision_reason TEXT,
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES runs(run_id),
    step_id UUID REFERENCES steps(step_id),
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Existing codebase already uses table name `artifacts`; to avoid collisions we use
-- action_artifacts for ACS immutable outputs.
CREATE TABLE IF NOT EXISTS action_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID REFERENCES steps(step_id),
    artifact_type VARCHAR(100) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    metadata JSONB NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
