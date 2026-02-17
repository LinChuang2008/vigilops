-- 012: 服务分类字段
-- 区分中间件(middleware)、业务系统(business)、基础设施(infrastructure)

ALTER TABLE services ADD COLUMN IF NOT EXISTS category VARCHAR(30);

-- 根据现有服务名自动填充分类
UPDATE services SET category = 'middleware'
WHERE category IS NULL AND (
    name ~* 'postgres|mysql|redis|rabbitmq|oracle|clickhouse|nacos|kafka|mongo|memcache|nginx|mq'
);

UPDATE services SET category = 'business'
WHERE category IS NULL AND (
    name ~* 'backend|frontend|api|service|app|admin|job'
);

-- 宿主机基础设施服务（nginx、sshd 等直接运行的进程）
UPDATE services SET category = 'infrastructure'
WHERE category IS NULL AND (
    name ~* 'nginx|httpd|apache|caddy|traefik|haproxy|keepalived|crond|ntpd'
);

UPDATE services SET category = 'infrastructure'
WHERE category IS NULL;
