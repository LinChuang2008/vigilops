-- Alert notification enhancement: cooldown + silence
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS cooldown_seconds INTEGER DEFAULT 300;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS silence_start TIME;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS silence_end TIME;

-- Notification channels table (if not exists - may already be created manually)
CREATE TABLE IF NOT EXISTS notification_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'webhook',
    config JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notification logs table
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id),
    channel_id INTEGER NOT NULL REFERENCES notification_channels(id),
    status VARCHAR(20) NOT NULL,
    response_code INTEGER,
    error TEXT,
    retries INTEGER DEFAULT 0,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notification_logs_alert_id ON notification_logs(alert_id);
