-- F062: Database monitoring tables

CREATE TABLE IF NOT EXISTS monitored_databases (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    db_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'unknown',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_monitored_databases_host_id ON monitored_databases(host_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_monitored_databases_host_name ON monitored_databases(host_id, name);

CREATE TABLE IF NOT EXISTS db_metrics (
    id BIGSERIAL PRIMARY KEY,
    database_id INTEGER NOT NULL REFERENCES monitored_databases(id) ON DELETE CASCADE,
    connections_total INTEGER,
    connections_active INTEGER,
    database_size_mb DOUBLE PRECISION,
    slow_queries INTEGER,
    tables_count INTEGER,
    transactions_committed BIGINT,
    transactions_rolled_back BIGINT,
    qps DOUBLE PRECISION,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_db_metrics_database_id ON db_metrics(database_id);
CREATE INDEX IF NOT EXISTS idx_db_metrics_recorded_at ON db_metrics(recorded_at);
