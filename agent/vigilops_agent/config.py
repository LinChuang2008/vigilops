"""Agent configuration loader."""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    url: str = "http://localhost:8001"
    token: str = ""


@dataclass
class HostConfig:
    name: str = ""
    tags: list[str] = field(default_factory=list)


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
class AgentConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    host: HostConfig = field(default_factory=HostConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    services: list[ServiceCheckConfig] = field(default_factory=list)


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
        sc = ServiceCheckConfig(
            name=svc.get("name", ""),
            type=svc.get("type", "http"),
            url=svc.get("url", ""),
            host=svc.get("host", ""),
            port=svc.get("port", 0),
            interval=_parse_interval(svc.get("interval", 30)),
            timeout=svc.get("timeout", 10),
        )
        cfg.services.append(sc)

    return cfg
