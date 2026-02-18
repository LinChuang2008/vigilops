-- 014: 自动修复日志表
-- 记录每次 AI 驱动的自动修复的完整生命周期

CREATE TABLE IF NOT EXISTS remediation_logs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id),
    host_id INTEGER REFERENCES hosts(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    risk_level VARCHAR(10),
    runbook_name VARCHAR(100),
    diagnosis_json JSONB,
    command_results_json JSONB,
    verification_passed BOOLEAN,
    blocked_reason TEXT,
    triggered_by VARCHAR(20) NOT NULL DEFAULT 'auto',
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_remediation_logs_alert_id ON remediation_logs(alert_id);
CREATE INDEX IF NOT EXISTS ix_remediation_logs_status ON remediation_logs(status);
CREATE INDEX IF NOT EXISTS ix_remediation_logs_created_at ON remediation_logs(created_at);
