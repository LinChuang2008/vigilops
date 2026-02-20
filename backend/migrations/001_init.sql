-- 001_init.sql: VigilOps base schema
-- Creates all core tables required for initial deployment

-- ── Hosts ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    os VARCHAR(100),
    os_version VARCHAR(100),
    arch VARCHAR(50),
    cpu_cores INTEGER,
    memory_total_mb INTEGER,
    agent_version VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'online',
    tags JSONB DEFAULT '{}',
    group_name VARCHAR(100),
    agent_token_id INTEGER NOT NULL,
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_hosts_hostname ON hosts(hostname);

-- ── Host Metrics ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS host_metrics (
    id BIGSERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES hosts(id),
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    memory_used_mb INTEGER,
    disk_percent DOUBLE PRECISION,
    disk_used_gb DOUBLE PRECISION,
    disk_total_gb DOUBLE PRECISION,
    load_1m DOUBLE PRECISION,
    load_5m DOUBLE PRECISION,
    load_15m DOUBLE PRECISION,
    process_count INTEGER,
    uptime_seconds BIGINT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_host_metrics_host_id ON host_metrics(host_id);
CREATE INDEX IF NOT EXISTS idx_host_metrics_collected_at ON host_metrics(collected_at);

-- ── Services ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    target VARCHAR(500) NOT NULL,
    check_interval INTEGER DEFAULT 60,
    timeout INTEGER DEFAULT 10,
    expected_status INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'unknown',
    host_id INTEGER,
    category VARCHAR(30),
    tags JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS service_checks (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms DOUBLE PRECISION,
    status_code INTEGER,
    error VARCHAR(500),
    checked_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_service_checks_service_id ON service_checks(service_id);
CREATE INDEX IF NOT EXISTS idx_service_checks_checked_at ON service_checks(checked_at);

-- ── Alert Rules & Alerts ──────────────────────────────────
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',
    metric VARCHAR(100) NOT NULL,
    operator VARCHAR(10) NOT NULL DEFAULT '>',
    threshold DOUBLE PRECISION NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 300,
    is_builtin BOOLEAN DEFAULT FALSE,
    is_enabled BOOLEAN DEFAULT TRUE,
    target_type VARCHAR(20) NOT NULL DEFAULT 'host',
    target_filter JSONB,
    cooldown_seconds INTEGER DEFAULT 300,
    silence_start TIME,
    silence_end TIME,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL,
    host_id INTEGER,
    service_id INTEGER,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'firing',
    message TEXT,
    metric_value DOUBLE PRECISION,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_rule_id ON alerts(rule_id);
CREATE INDEX IF NOT EXISTS idx_alerts_host_id ON alerts(host_id);
CREATE INDEX IF NOT EXISTS idx_alerts_service_id ON alerts(service_id);

-- ── Notification Channels & Logs ──────────────────────────
CREATE TABLE IF NOT EXISTS notification_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'webhook',
    config JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_code INTEGER,
    error TEXT,
    retries INTEGER DEFAULT 0,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notification_logs_alert_id ON notification_logs(alert_id);

-- ── Settings ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    description VARCHAR(500),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Agent Tokens ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_tokens (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- ── Schema Migrations Tracking ────────────────────────────
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
