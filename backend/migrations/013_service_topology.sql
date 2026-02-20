-- 服务依赖关系表
CREATE TABLE IF NOT EXISTS service_dependencies (
    id SERIAL PRIMARY KEY,
    source_service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    target_service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'calls',  -- calls / depends_on / publishes_to
    description VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_service_id, target_service_id)
);
CREATE INDEX IF NOT EXISTS idx_svc_dep_source ON service_dependencies(source_service_id);
CREATE INDEX IF NOT EXISTS idx_svc_dep_target ON service_dependencies(target_service_id);
