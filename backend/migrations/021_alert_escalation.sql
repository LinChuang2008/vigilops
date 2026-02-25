-- 告警升级和值班排期表结构 (Alert Escalation and On-Call Schedule Tables)
-- Migration: 021_alert_escalation.sql

-- 值班组表 (On-Call Group Table)
CREATE TABLE on_call_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 值班排期表 (On-Call Schedule Table) 
CREATE TABLE on_call_schedules (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES on_call_groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, start_date, end_date)
);

-- 升级规则表 (Escalation Rule Table)
CREATE TABLE escalation_rules (
    id SERIAL PRIMARY KEY,
    alert_rule_id INTEGER REFERENCES alert_rules(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    is_enabled BOOLEAN DEFAULT true,
    escalation_levels JSON NOT NULL, -- [{"level": 1, "delay_minutes": 15, "severity": "high"}, ...]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 告警升级记录表 (Alert Escalation Log Table)
CREATE TABLE alert_escalations (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
    escalation_rule_id INTEGER REFERENCES escalation_rules(id) ON DELETE SET NULL,
    from_severity VARCHAR(20) NOT NULL,
    to_severity VARCHAR(20) NOT NULL,
    escalation_level INTEGER NOT NULL,
    escalated_at TIMESTAMPTZ DEFAULT NOW(),
    escalated_by_system BOOLEAN DEFAULT true,
    message TEXT
);

-- 修改alerts表，添加升级相关字段 (Modify alerts table for escalation)
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS escalation_level INTEGER DEFAULT 0;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS last_escalated_at TIMESTAMPTZ;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS next_escalation_at TIMESTAMPTZ;

-- 创建索引以提高查询性能 (Create indexes for better performance)
CREATE INDEX idx_on_call_schedules_date_range ON on_call_schedules(start_date, end_date);
CREATE INDEX idx_on_call_schedules_user_id ON on_call_schedules(user_id);
CREATE INDEX idx_alerts_next_escalation ON alerts(next_escalation_at) WHERE next_escalation_at IS NOT NULL;
CREATE INDEX idx_alert_escalations_alert_id ON alert_escalations(alert_id);

-- 插入示例数据 (Insert sample data)

-- 示例值班组 (Sample On-Call Groups)
INSERT INTO on_call_groups (name, description) VALUES 
('运维一组', '负责核心业务系统的运维支持'),
('运维二组', '负责基础设施和数据库维护'),
('开发支持组', '提供应用程序问题的技术支持');

-- 示例升级规则 (Sample Escalation Rules)
-- 为已存在的告警规则添加升级配置
INSERT INTO escalation_rules (alert_rule_id, name, escalation_levels)
SELECT id, name || ' 升级规则', 
       '[
         {"level": 1, "delay_minutes": 15, "severity": "medium"},
         {"level": 2, "delay_minutes": 30, "severity": "high"}, 
         {"level": 3, "delay_minutes": 60, "severity": "critical"}
       ]'::json
FROM alert_rules 
WHERE severity IN ('low', 'medium') 
LIMIT 3;

COMMENT ON TABLE on_call_groups IS '值班组管理表，定义不同的值班小组';
COMMENT ON TABLE on_call_schedules IS '值班排期表，记录具体的值班安排';
COMMENT ON TABLE escalation_rules IS '告警升级规则配置表';
COMMENT ON TABLE alert_escalations IS '告警升级历史记录表';