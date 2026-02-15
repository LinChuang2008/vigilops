"""Agent configuration loader."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class ServerConfig:
    url: str = "http://localhost:8001"
    token: str = ""


@dataclass
class HostConfig:
    name: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class MetricsConfig:
    interval: int = 15  # seconds


@dataclass
class ServiceCheckConfig:
    name: str = ""
    type: str = "http"  # http / tcp
    url: str = ""
    host: str = ""
    port: int = 0
    interval: int = 30  # seconds
    timeout: int = 10


@dataclass
class LogSourceConfig:
    path: str = ""           # 日志文件路径，如 /var/log/app.log
    service: str = ""        # 服务名
    multiline: bool = False  # 是否启用多行合并
    multiline_pattern: str = "^\\d{4}-\\d{2}-\\d{2}|^\\["  # 新日志行起始pattern
    docker: bool = False     # 是否为 Docker json-log 格式


@dataclass
class DiscoveryConfig:
    docker: bool = True  # Auto-discover Docker containers
    interval: int = 30   # Default check interval for discovered services


@dataclass
class DatabaseMonitorConfig:
    name: str = ""          # display name
    type: str = "postgres"  # postgres / mysql
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    interval: int = 60      # collection interval seconds
    container_name: str = ""  # Docker container name (for Oracle)
    oracle_sid: str = ""      # Oracle SID
    oracle_home: str = ""     # ORACLE_HOME (optional, defaults to .bash_profile)


@dataclass
class AgentConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    host: HostConfig = field(default_factory=HostConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    services: List[ServiceCheckConfig] = field(default_factory=list)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    log_sources: List[LogSourceConfig] = field(default_factory=list)
    databases: List[DatabaseMonitorConfig] = field(default_factory=list)


def _parse_interval(val) -> int:
    """Parse interval like '15s', '1m', or int."""
    if isinstance(val, int):
        return val
    s = str(val).strip().lower()
    if s.endswith("s"):
        return int(s[:-1])
    if s.endswith("m"):
        return int(s[:-1]) * 60
    return int(s)


def load_config(path: str) -> AgentConfig:
    """Load config from YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(p) as f:
        data = yaml.safe_load(f) or {}

    cfg = AgentConfig()

    # Server
    srv = data.get("server", {})
    cfg.server.url = srv.get("url", cfg.server.url).rstrip("/")
    cfg.server.token = os.environ.get("VIGILOPS_TOKEN", srv.get("token", ""))

    # Host
    h = data.get("host", {})
    cfg.host.name = h.get("name", "")
    cfg.host.tags = h.get("tags", [])

    # Metrics
    m = data.get("metrics", {})
    cfg.metrics.interval = _parse_interval(m.get("interval", 15))

    # Services
    for svc in data.get("services", []):
        svc_type = svc.get("type", "http")
        target = svc.get("target", "")
        url = svc.get("url", "")
        host = svc.get("host", "")
        port = svc.get("port", 0)

        # Parse 'target' shorthand: "http://..." → url, "host:port" → host+port
        if target and not url and not host:
            if target.startswith("http://") or target.startswith("https://"):
                url = target
            elif ":" in target:
                parts = target.rsplit(":", 1)
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    host = target

        sc = ServiceCheckConfig(
            name=svc.get("name", ""),
            type=svc_type,
            url=url,
            host=host,
            port=port,
            interval=_parse_interval(svc.get("interval", 30)),
            timeout=svc.get("timeout", 10),
        )
        cfg.services.append(sc)

    # Discovery
    disc = data.get("discovery", {})
    if isinstance(disc, bool):
        cfg.discovery.docker = disc
    elif isinstance(disc, dict):
        cfg.discovery.docker = disc.get("docker", True)
        cfg.discovery.interval = _parse_interval(disc.get("interval", 30))

    # Log sources
    for src in data.get("log_sources", []):
        ls = LogSourceConfig(
            path=src.get("path", ""),
            service=src.get("service", ""),
            multiline=src.get("multiline", False),
            multiline_pattern=src.get("multiline_pattern", LogSourceConfig.multiline_pattern),
            docker=src.get("docker", False),
        )
        if ls.path:
            cfg.log_sources.append(ls)

    # Databases
    for db_conf in data.get("databases", []):
        db_type = db_conf.get("type", "postgres")
        default_port = 3306 if db_type == "mysql" else 5432
        dmc = DatabaseMonitorConfig(
            name=db_conf.get("name", ""),
            type=db_type,
            host=db_conf.get("host", "localhost"),
            port=db_conf.get("port", default_port),
            database=db_conf.get("database", ""),
            username=db_conf.get("username", ""),
            password=db_conf.get("password", ""),
            interval=_parse_interval(db_conf.get("interval", 60)),
            container_name=db_conf.get("container_name", ""),
            oracle_sid=db_conf.get("oracle_sid", ""),
            oracle_home=db_conf.get("oracle_home", ""),
        )
        cfg.databases.append(dmc)

    return cfg
