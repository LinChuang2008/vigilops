-- 022: Dashboard Configuration Tables
-- 添加仪表盘配置表，支持用户自定义Dashboard布局

-- 仪表盘组件定义表
CREATE TABLE IF NOT EXISTS dashboard_components (
    id VARCHAR(50) PRIMARY KEY,  -- 组件ID，如 "metrics_cards", "server_overview"
    name VARCHAR(100) NOT NULL,  -- 组件显示名称
    description VARCHAR(255),    -- 组件描述
    category VARCHAR(50),        -- 组件分类：metrics, charts, tables, alerts
    default_config JSONB,        -- 默认配置，如位置、大小等
    is_enabled BOOLEAN DEFAULT TRUE,  -- 是否启用
    sort_order INTEGER DEFAULT 0,     -- 排序权重
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 仪表盘布局配置表
CREATE TABLE IF NOT EXISTS dashboard_layouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- 布局名称
    description VARCHAR(255),    -- 布局描述
    is_active BOOLEAN DEFAULT FALSE,  -- 是否为当前激活的布局
    is_preset BOOLEAN DEFAULT FALSE,  -- 是否为预设模板
    grid_cols INTEGER DEFAULT 24,     -- 网格列数（Ant Design 栅格系统）
    config JSONB NOT NULL,            -- 布局配置 JSON
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 确保每个用户只能有一个激活的布局
    CONSTRAINT unique_user_active_layout UNIQUE (user_id, is_active) DEFERRABLE INITIALLY DEFERRED
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_dashboard_layouts_user_id ON dashboard_layouts(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_layouts_active ON dashboard_layouts(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_dashboard_components_enabled ON dashboard_components(is_enabled, sort_order);

-- 插入默认组件配置
INSERT INTO dashboard_components (id, name, description, category, default_config, is_enabled, sort_order)
VALUES
    ('metrics_cards', '核心指标卡片', '显示服务器、服务、数据库、告警等核心指标', 'metrics', '{"position": {"row": 0, "col": 0, "span": 24}, "visible": true}', true, 1),
    ('health_score', '健康评分', '系统整体健康评分和状态', 'metrics', '{"position": {"row": 0, "col": 20, "span": 4}, "visible": true}', true, 2),
    ('server_overview', '服务器总览', '服务器健康状态和关键指标总览', 'metrics', '{"position": {"row": 1, "col": 0, "span": 24}, "visible": true}', true, 3),
    ('trends_charts', '24小时趋势', 'CPU、内存、告警、错误日志趋势图', 'charts', '{"position": {"row": 2, "col": 0, "span": 24}, "visible": true}', true, 4),
    ('resource_compare', '资源使用率对比', '多服务器资源使用情况对比图表', 'charts', '{"position": {"row": 3, "col": 0, "span": 12}, "visible": true}', true, 5),
    ('network_bandwidth', '网络带宽', '服务器网络带宽使用情况', 'charts', '{"position": {"row": 3, "col": 12, "span": 12}, "visible": true}', true, 6),
    ('log_stats', '日志统计', '日志数量和错误统计', 'tables', '{"position": {"row": 4, "col": 0, "span": 12}, "visible": true}', true, 7),
    ('recent_alerts', '最新告警', '最近的告警事件列表', 'alerts', '{"position": {"row": 4, "col": 12, "span": 12}, "visible": true}', true, 8)
ON CONFLICT (id) DO NOTHING;

-- 为现有用户创建默认布局（使用当前的默认配置）
INSERT INTO dashboard_layouts (user_id, name, description, is_active, is_preset, grid_cols, config)
SELECT 
    u.id as user_id,
    '默认布局' as name,
    '系统默认的仪表盘布局' as description,
    true as is_active,
    false as is_preset,
    24 as grid_cols,
    '{
        "components": [
            {"id": "metrics_cards", "position": {"row": 0, "col": 0, "span": 24}, "visible": true},
            {"id": "server_overview", "position": {"row": 1, "col": 0, "span": 24}, "visible": true},
            {"id": "trends_charts", "position": {"row": 2, "col": 0, "span": 24}, "visible": true},
            {"id": "resource_compare", "position": {"row": 3, "col": 0, "span": 12}, "visible": true},
            {"id": "network_bandwidth", "position": {"row": 3, "col": 12, "span": 12}, "visible": true},
            {"id": "log_stats", "position": {"row": 4, "col": 0, "span": 12}, "visible": true},
            {"id": "recent_alerts", "position": {"row": 4, "col": 12, "span": 12}, "visible": true}
        ]
    }'::jsonb as config
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM dashboard_layouts dl 
    WHERE dl.user_id = u.id AND dl.is_active = true
);

-- 更新触发器：自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_dashboard_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_dashboard_layouts_updated_at 
    BEFORE UPDATE ON dashboard_layouts 
    FOR EACH ROW EXECUTE FUNCTION update_dashboard_updated_at_column();

CREATE TRIGGER update_dashboard_components_updated_at 
    BEFORE UPDATE ON dashboard_components 
    FOR EACH ROW EXECUTE FUNCTION update_dashboard_updated_at_column();

-- 触发器：确保用户只有一个激活的布局
CREATE OR REPLACE FUNCTION ensure_single_active_layout()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果新布局被设置为激活，取消同用户的其他激活布局
    IF NEW.is_active = true THEN
        UPDATE dashboard_layouts 
        SET is_active = false 
        WHERE user_id = NEW.user_id 
          AND id != NEW.id 
          AND is_active = true;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER ensure_single_active_layout_trigger
    BEFORE INSERT OR UPDATE ON dashboard_layouts
    FOR EACH ROW EXECUTE FUNCTION ensure_single_active_layout();

COMMENT ON TABLE dashboard_components IS '仪表盘组件定义表';
COMMENT ON TABLE dashboard_layouts IS '仪表盘布局配置表';
COMMENT ON COLUMN dashboard_layouts.config IS '布局配置JSON，包含组件位置、可见性等信息';
COMMENT ON COLUMN dashboard_layouts.grid_cols IS '网格列数，基于Ant Design栅格系统';
COMMENT ON CONSTRAINT unique_user_active_layout ON dashboard_layouts IS '确保每个用户只能有一个激活的布局';