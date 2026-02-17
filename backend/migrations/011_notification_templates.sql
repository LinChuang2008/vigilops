-- 011: 通知模板表
-- 支持多渠道通知模板管理（Phase 4C）

CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,  -- webhook / email / dingtalk / feishu / wecom / all
    subject_template VARCHAR(500),       -- 邮件标题模板（仅 email 使用）
    body_template TEXT NOT NULL,          -- 消息体模板
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE notification_templates IS '通知模板表';
COMMENT ON COLUMN notification_templates.channel_type IS '渠道类型: webhook/email/dingtalk/feishu/wecom/all';
COMMENT ON COLUMN notification_templates.body_template IS '消息体模板，支持变量 {title} {severity} {message} {metric_value} {threshold} {host_id} {fired_at}';
