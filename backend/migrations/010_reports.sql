-- 010_reports.sql
-- 运维报告表：存储 AI 自动生成的日报和周报

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    report_type VARCHAR(20) NOT NULL,          -- 'daily' / 'weekly'
    period_start DATETIME NOT NULL,
    period_end DATETIME NOT NULL,
    content TEXT NOT NULL DEFAULT '',           -- Markdown 报告正文
    summary TEXT NOT NULL DEFAULT '',           -- AI 生成的简短摘要
    status VARCHAR(20) NOT NULL DEFAULT 'generating',  -- generating / completed / failed
    generated_by INTEGER,                      -- 手动触发时的 user_id
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 按类型和时间段查询索引
CREATE INDEX IF NOT EXISTS idx_reports_type_period ON reports (report_type, period_start, period_end);
-- 按创建时间倒序排列索引
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports (created_at DESC);
