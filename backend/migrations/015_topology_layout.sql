-- 013: 拓扑图自定义布局存储
-- 每个用户可以保存自己的拓扑图节点位置

CREATE TABLE IF NOT EXISTS topology_layouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) DEFAULT 'default',
    -- 节点位置 JSON: {"node_id": {"x": 100, "y": 200}, ...}
    positions JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name)
);
