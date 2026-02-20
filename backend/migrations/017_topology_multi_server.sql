-- 015: Multi-server topology tables
-- servers, service_groups, server_services, nginx_upstreams

CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45),
    label VARCHAR(255),
    tags JSONB DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    last_seen TIMESTAMPTZ,
    is_simulated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_servers_hostname ON servers(hostname);

CREATE TABLE IF NOT EXISTS service_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_service_groups_name ON service_groups(name);

CREATE TABLE IF NOT EXISTS server_services (
    id SERIAL PRIMARY KEY,
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES service_groups(id) ON DELETE CASCADE,
    port INTEGER,
    pid INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    cpu_percent FLOAT DEFAULT 0,
    mem_mb FLOAT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(server_id, group_id, port)
);
CREATE INDEX IF NOT EXISTS idx_server_services_server ON server_services(server_id);
CREATE INDEX IF NOT EXISTS idx_server_services_group ON server_services(group_id);

CREATE TABLE IF NOT EXISTS nginx_upstreams (
    id SERIAL PRIMARY KEY,
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    upstream_name VARCHAR(255) NOT NULL,
    backend_address VARCHAR(255) NOT NULL,
    weight INTEGER DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'up',
    parsed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_nginx_upstreams_server ON nginx_upstreams(server_id);
CREATE INDEX IF NOT EXISTS idx_nginx_upstreams_name ON nginx_upstreams(upstream_name);

-- Add server_id to host_metrics for multi-server support
ALTER TABLE host_metrics ADD COLUMN IF NOT EXISTS server_id INTEGER REFERENCES servers(id);
CREATE INDEX IF NOT EXISTS idx_host_metrics_server ON host_metrics(server_id);
