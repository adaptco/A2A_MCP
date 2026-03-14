-- Charley Fox Pizza JRPG Database Schema
-- PostgreSQL initialization script

-- ============================================================================
-- SESSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_name VARCHAR(255) NOT NULL DEFAULT 'Charley Fox Guild',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_quests TEXT[] DEFAULT '{}',
    gold INTEGER DEFAULT 0,
    heat INTEGER DEFAULT 28,
    progress INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    current_phase VARCHAR(50) DEFAULT 'opening',
    INDEX idx_sessions_created_at (created_at),
    INDEX idx_sessions_updated_at (updated_at)
);

-- ============================================================================
-- QUESTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS quests (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    reward INTEGER NOT NULL,
    effort INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_quests_phase (phase),
    INDEX idx_quests_role (role)
);

-- ============================================================================
-- QUEST COMPLETIONS TABLE (Audit Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS quest_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    quest_id VARCHAR(50) NOT NULL REFERENCES quests(id),
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    role VARCHAR(50),
    phase VARCHAR(50),
    reward_granted INTEGER,
    INDEX idx_quest_completions_session (session_id),
    INDEX idx_quest_completions_quest (quest_id),
    INDEX idx_quest_completions_completed_at (completed_at)
);

-- ============================================================================
-- WORKFLOW EVENTS TABLE (Detailed Event Log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    role VARCHAR(50),
    phase VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL DEFAULT '{}',
    INDEX idx_workflow_events_session (session_id),
    INDEX idx_workflow_events_type (event_type),
    INDEX idx_workflow_events_created_at (created_at),
    INDEX idx_workflow_events_data (data, created_at)
);

-- ============================================================================
-- GAME STATE SNAPSHOTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_state_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    phase VARCHAR(50),
    gold INTEGER,
    heat INTEGER,
    progress INTEGER,
    INDEX idx_game_state_snapshots_session (session_id),
    INDEX idx_game_state_snapshots_created_at (created_at)
);

-- ============================================================================
-- ORDERS TABLE (Pizza Orders)
-- ============================================================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    customer_name VARCHAR(255),
    items JSONB NOT NULL DEFAULT '[]',
    total_price NUMERIC(10, 2),
    order_status VARCHAR(50) DEFAULT 'pending',
    promised_delivery_time TIMESTAMP WITH TIME ZONE,
    actual_delivery_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    INDEX idx_orders_session (session_id),
    INDEX idx_orders_status (order_status),
    INDEX idx_orders_created_at (created_at)
);

-- ============================================================================
-- DELIVERY ROUTES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS delivery_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    driver_name VARCHAR(255),
    route_status VARCHAR(50) DEFAULT 'pending',
    orders JSONB NOT NULL DEFAULT '[]',
    total_stops INTEGER,
    completed_stops INTEGER DEFAULT 0,
    estimated_completion_time TIMESTAMP WITH TIME ZONE,
    actual_completion_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_delivery_routes_session (session_id),
    INDEX idx_delivery_routes_status (route_status)
);

-- ============================================================================
-- KITCHEN QUEUE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS kitchen_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    queue_position INTEGER,
    status VARCHAR(50) DEFAULT 'waiting',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_kitchen_queue_session (session_id),
    INDEX idx_kitchen_queue_order (order_id),
    INDEX idx_kitchen_queue_status (status)
);

-- ============================================================================
-- VECTOR EMBEDDINGS TABLE (For RAG/Retrieval)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    content_type VARCHAR(100) NOT NULL,
    content_id VARCHAR(255),
    content_text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vector_embeddings_session (session_id),
    INDEX idx_vector_embeddings_type (content_type),
    INDEX idx_vector_embeddings_created_at (created_at)
);

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,
    actor_role VARCHAR(50),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    changes JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    INDEX idx_audit_logs_session (session_id),
    INDEX idx_audit_logs_action (action),
    INDEX idx_audit_logs_created_at (created_at)
);

-- ============================================================================
-- INSERT INITIAL QUEST DATA
-- ============================================================================
INSERT INTO quests (id, title, phase, reward, effort, role, description) VALUES
('q1', 'Unlock the Oven Keep', 'opening', 15, 10, 'manager', 'Open shift, verify checklist, warm POS, confirm store state.'),
('q2', 'Dough Circle Ritual', 'prep', 25, 20, 'cooks', 'Prep dough, cheese, sauce, boxes, and side items before lunch spike.'),
('q3', 'Crystal Phone Queue', 'orders', 20, 15, 'foh', 'Accept calls, web orders, and counter demand with ETA promises.'),
('q4', 'Inferno Throughput', 'baking', 30, 25, 'cooks', 'Sequence oven loads to prevent bottlenecks while preserving quality.'),
('q5', 'Moped of the Red Fox', 'delivery', 35, 25, 'delivery', 'Bundle route stops, confirm addresses, and complete hot handoff.'),
('q6', 'Coins of Closing', 'payment', 18, 12, 'owner', 'Close register, reconcile card settlements, capture variance and tip flow.')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sessions_party_name ON sessions(party_name);
CREATE INDEX IF NOT EXISTS idx_quest_completions_compound ON quest_completions(session_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_events_compound ON workflow_events(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_compound ON orders(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_delivery_routes_compound ON delivery_routes(session_id, created_at DESC);

-- ============================================================================
-- CREATE MATERIALIZED VIEWS FOR ANALYTICS
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS session_statistics AS
SELECT
    s.id,
    s.party_name,
    s.created_at,
    s.updated_at,
    s.gold,
    s.heat,
    s.progress,
    COUNT(DISTINCT qc.quest_id) as total_quests_completed,
    COUNT(DISTINCT o.id) as total_orders,
    COUNT(DISTINCT dr.id) as total_deliveries,
    EXTRACT(EPOCH FROM (s.updated_at - s.created_at)) as session_duration_seconds
FROM sessions s
LEFT JOIN quest_completions qc ON s.id = qc.session_id
LEFT JOIN orders o ON s.id = o.session_id
LEFT JOIN delivery_routes dr ON s.id = dr.session_id
GROUP BY s.id, s.party_name, s.created_at, s.updated_at, s.gold, s.heat, s.progress;

CREATE INDEX IF NOT EXISTS idx_session_statistics ON session_statistics(id);
