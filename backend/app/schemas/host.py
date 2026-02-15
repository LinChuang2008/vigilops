from datetime import datetime
from pydantic import BaseModel


class HostResponse(BaseModel):
    id: int
    hostname: str
    ip_address: str | None = None
    os: str | None = None
    os_version: str | None = None
    arch: str | None = None
    cpu_cores: int | None = None
    memory_total_mb: int | None = None
    agent_version: str | None = None
    status: str
    tags: dict | None = None
    group_name: str | None = None
    last_heartbeat: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HostWithMetrics(HostResponse):
    """Host with latest metrics from Redis."""
    latest_metrics: dict | None = None


class HostMetricResponse(BaseModel):
    id: int
    host_id: int
    cpu_percent: float | None = None
    cpu_load_1: float | None = None
    cpu_load_5: float | None = None
    cpu_load_15: float | None = None
    memory_used_mb: int | None = None
    memory_percent: float | None = None
    disk_used_mb: int | None = None
    disk_total_mb: int | None = None
    disk_percent: float | None = None
    net_bytes_sent: int | None = None
    net_bytes_recv: int | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}
