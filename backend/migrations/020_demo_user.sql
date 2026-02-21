-- 020: 创建 demo 体验账号（只读 viewer 角色）
-- demo@vigilops.io / demo123

INSERT INTO users (email, name, hashed_password, role, is_active)
VALUES (
    'demo@vigilops.io',
    'Demo User',
    '$2b$12$b9yKdxJUXelEwmCoWMkN0.wyxoOiLsGZ6AGvgHgbLv5K2HiEDGa5a',
    'viewer',
    true
)
ON CONFLICT (email) DO NOTHING;
