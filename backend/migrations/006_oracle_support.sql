-- Oracle database monitoring support
ALTER TABLE db_metrics ADD COLUMN IF NOT EXISTS tablespace_used_pct FLOAT;
ALTER TABLE monitored_databases ADD COLUMN IF NOT EXISTS slow_queries_detail JSON;
