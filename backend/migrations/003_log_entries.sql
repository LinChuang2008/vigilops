-- Migration 003: Log entries table
CREATE TABLE IF NOT EXISTS log_entries (
    id BIGSERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id),
    service VARCHAR(255),
    source VARCHAR(512),
    level VARCHAR(20),
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_log_entries_host_id ON log_entries(host_id);
CREATE INDEX IF NOT EXISTS ix_log_entries_service ON log_entries(service);
CREATE INDEX IF NOT EXISTS ix_log_entries_level ON log_entries(level);
CREATE INDEX IF NOT EXISTS ix_log_entries_timestamp ON log_entries(timestamp);
CREATE INDEX IF NOT EXISTS ix_log_entries_host_timestamp ON log_entries(host_id, timestamp DESC);
