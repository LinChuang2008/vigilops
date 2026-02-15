-- F069/F071: Enhanced alert rules for log keyword and database metric alerts
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS rule_type VARCHAR(20) DEFAULT 'metric';
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS log_keyword VARCHAR(500);
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS log_level VARCHAR(20);
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS log_service VARCHAR(255);
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS db_metric_name VARCHAR(50);
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS db_id INTEGER;

-- Make metric/operator/threshold nullable for non-metric rule types
ALTER TABLE alert_rules ALTER COLUMN metric SET DEFAULT '';
ALTER TABLE alert_rules ALTER COLUMN threshold SET DEFAULT 0;

-- Default existing rows
UPDATE alert_rules SET rule_type = 'metric' WHERE rule_type IS NULL;
