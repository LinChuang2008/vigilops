-- SLA 规则表
CREATE TABLE IF NOT EXISTS sla_rules (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    target_percent NUMERIC(5,2) NOT NULL DEFAULT 99.90,  -- 目标可用率如 99.90%
    calculation_window VARCHAR(20) DEFAULT 'monthly',     -- monthly / weekly / daily
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(service_id)
);

-- SLA 违规事件表
CREATE TABLE IF NOT EXISTS sla_violations (
    id SERIAL PRIMARY KEY,
    sla_rule_id INTEGER NOT NULL REFERENCES sla_rules(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    description VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sla_violations_rule ON sla_violations(sla_rule_id);
CREATE INDEX IF NOT EXISTS idx_sla_violations_started ON sla_violations(started_at);
