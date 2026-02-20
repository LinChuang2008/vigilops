-- 016: Default alert rules seed data
-- 内置告警规则种子数据（幂等：按 name 判断是否已存在）

INSERT INTO alert_rules (name, description, severity, metric, operator, threshold, duration_seconds, is_builtin, is_enabled, target_type, rule_type, cooldown_seconds)
SELECT * FROM (VALUES
    ('CPU 使用率过高'::VARCHAR, 'CPU 使用率超过 90% 持续 5 分钟'::TEXT, 'critical'::VARCHAR, 'cpu_percent'::VARCHAR, '>'::VARCHAR, 90::FLOAT, 300, TRUE, TRUE, 'host'::VARCHAR, 'metric'::VARCHAR, 300),
    ('内存使用率过高', '内存使用率超过 85% 持续 5 分钟', 'warning', 'memory_percent', '>', 85, 300, TRUE, TRUE, 'host', 'metric', 300),
    ('磁盘使用率过高', '磁盘使用率超过 90%', 'critical', 'disk_percent', '>', 90, 0, TRUE, TRUE, 'host', 'metric', 300),
    ('主机离线', '主机失去连接', 'critical', 'host_alive', '==', 0, 0, TRUE, TRUE, 'host', 'metric', 600),
    ('系统负载过高', '系统负载超过 CPU 核数的 2 倍，持续 10 分钟', 'warning', 'load_per_cpu', '>', 2, 600, TRUE, TRUE, 'host', 'metric', 300)
) AS v(name, description, severity, metric, operator, threshold, duration_seconds, is_builtin, is_enabled, target_type, rule_type, cooldown_seconds)
WHERE NOT EXISTS (SELECT 1 FROM alert_rules ar WHERE ar.name = v.name);
