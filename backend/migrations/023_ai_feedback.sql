-- 023: AI Feedback System
-- 添加 AI 反馈系统，收集用户对 AI 分析结果的反馈，用于改进 AI 服务质量

-- AI 反馈表
CREATE TABLE IF NOT EXISTS ai_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- AI 交互信息
    session_id VARCHAR(100),  -- 对话会话 ID
    message_id VARCHAR(100),  -- 消息 ID
    ai_response TEXT NOT NULL,  -- AI 回答内容
    user_question TEXT,  -- 用户问题
    
    -- 反馈内容
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),  -- 评分：1-5
    feedback_type VARCHAR(50) NOT NULL DEFAULT 'general',  -- 反馈类型
    feedback_text TEXT,  -- 文字反馈
    is_helpful BOOLEAN,  -- 是否有帮助
    
    -- 上下文信息
    context JSONB,  -- 问题上下文
    ai_confidence REAL CHECK (ai_confidence >= 0 AND ai_confidence <= 1),  -- AI 置信度
    response_time_ms INTEGER CHECK (response_time_ms >= 0),  -- 响应时间（毫秒）
    
    -- 处理状态
    is_reviewed BOOLEAN DEFAULT FALSE,  -- 是否已审核
    reviewer_notes TEXT,  -- 审核备注
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI 反馈统计汇总表
CREATE TABLE IF NOT EXISTS ai_feedback_summary (
    id SERIAL PRIMARY KEY,
    
    -- 统计周期
    period_type VARCHAR(20) NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- 统计数据
    total_feedback INTEGER DEFAULT 0,
    avg_rating REAL,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    
    -- 按类型统计
    feedback_by_type JSONB,  -- {"general": 10, "accuracy": 5, ...}
    rating_distribution JSONB,  -- {"1": 2, "2": 5, "3": 10, ...}
    
    -- 性能指标
    avg_response_time_ms REAL,
    avg_confidence REAL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 防止重复统计同一周期
    UNIQUE(period_type, period_start, period_end)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_id ON ai_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_session_id ON ai_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_message_id ON ai_feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_rating ON ai_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_type ON ai_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_helpful ON ai_feedback(is_helpful);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_created_at ON ai_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_summary_period ON ai_feedback_summary(period_type, period_start);

-- 更新触发器：自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_ai_feedback_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ai_feedback_updated_at 
    BEFORE UPDATE ON ai_feedback 
    FOR EACH ROW EXECUTE FUNCTION update_ai_feedback_updated_at_column();

-- 插入示例反馈类型的检查约束数据
ALTER TABLE ai_feedback ADD CONSTRAINT check_feedback_type 
CHECK (feedback_type IN ('general', 'accuracy', 'relevance', 'clarity', 'quick', 'detailed'));

-- 添加一些示例统计函数（可选）
CREATE OR REPLACE VIEW ai_feedback_stats_view AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_feedback,
    ROUND(AVG(rating), 2) as avg_rating,
    COUNT(CASE WHEN is_helpful = TRUE THEN 1 END) as helpful_count,
    COUNT(CASE WHEN is_helpful = FALSE THEN 1 END) as not_helpful_count,
    ROUND(AVG(response_time_ms), 0) as avg_response_time_ms,
    ROUND(AVG(ai_confidence), 3) as avg_confidence,
    
    -- 评分分布
    COUNT(CASE WHEN rating = 1 THEN 1 END) as rating_1,
    COUNT(CASE WHEN rating = 2 THEN 1 END) as rating_2,
    COUNT(CASE WHEN rating = 3 THEN 1 END) as rating_3,
    COUNT(CASE WHEN rating = 4 THEN 1 END) as rating_4,
    COUNT(CASE WHEN rating = 5 THEN 1 END) as rating_5
FROM ai_feedback 
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC;

COMMENT ON TABLE ai_feedback IS 'AI 反馈表 - 存储用户对 AI 分析结果的反馈';
COMMENT ON TABLE ai_feedback_summary IS 'AI 反馈统计汇总表 - 定期汇总的反馈统计数据';
COMMENT ON COLUMN ai_feedback.rating IS '用户评分：1(很差) 2(差) 3(一般) 4(好) 5(很好)';
COMMENT ON COLUMN ai_feedback.feedback_type IS '反馈类型：general(一般), accuracy(准确性), relevance(相关性), clarity(清晰度), quick(快速), detailed(详细)';
COMMENT ON COLUMN ai_feedback.context IS '问题上下文信息，如相关告警、系统状态等';
COMMENT ON COLUMN ai_feedback.ai_confidence IS 'AI 回答的置信度，范围 0-1';
COMMENT ON VIEW ai_feedback_stats_view IS 'AI 反馈统计视图 - 按日期聚合的反馈统计数据';