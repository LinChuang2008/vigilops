-- AI Insights table for storing AI analysis results
CREATE TABLE IF NOT EXISTS ai_insights (
    id SERIAL PRIMARY KEY,
    insight_type VARCHAR(50) NOT NULL,          -- anomaly / root_cause / chat
    severity VARCHAR(20) NOT NULL DEFAULT 'info', -- info / warning / critical
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    details JSONB,
    related_host_id INTEGER REFERENCES hosts(id) ON DELETE SET NULL,
    related_alert_id INTEGER REFERENCES alerts(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'new',  -- new / acknowledged / resolved
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_insights_type ON ai_insights(insight_type);
CREATE INDEX idx_ai_insights_severity ON ai_insights(severity);
CREATE INDEX idx_ai_insights_status ON ai_insights(status);
CREATE INDEX idx_ai_insights_created_at ON ai_insights(created_at);
CREATE INDEX idx_ai_insights_host_id ON ai_insights(related_host_id);
