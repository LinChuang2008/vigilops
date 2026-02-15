from datetime import datetime
from pydantic import BaseModel


class AgentRegisterRequest(BaseModel):
    hostname: str
    ip_address: str | None = None
    os: str | None = None
    os_version: str | None = None
    arch: str | None = None
    cpu_cores: int | None = None
    memory_total_mb: int | None = None
    agent_version: str | None = None
    tags: dict | None = None
    group_name: str | None = None


class AgentRegisterResponse(BaseModel):
    host_id: int
    hostname: str
    status: str
    created: bool  # True if newly created, False if already existed

    model_config = {"from_attributes": True}


class AgentHeartbeatRequest(BaseModel):
    host_id: int


class AgentHeartbeatResponse(BaseModel):
    status: str
    server_time: datetime
    heartbeat_interval: int = 60  # seconds


class MetricReport(BaseModel):
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
    timestamp: datetime | None = None
