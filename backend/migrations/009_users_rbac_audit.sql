-- 009: 用户管理 RBAC + 审计日志
-- Phase 4A: 扩展角色体系，新增审计日志表

-- users 表 role 字段已是 varchar(20)，无需 ALTER
-- 将现有 role='user' 的用户更新为 'viewer'
UPDATE users SET role = 'viewer' WHERE role = 'user';

-- 创建审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    action      VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER,
    detail      TEXT,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
