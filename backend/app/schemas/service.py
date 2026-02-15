from datetime import datetime
from pydantic import BaseModel


class ServiceResponse(BaseModel):
    id: int
    name: str
    type: str
    target: str
    check_interval: int
    timeout: int
    expected_status: int | None = None
    is_active: bool
    status: str
    host_id: int | None = None
    tags: dict | None = None
    created_at: datetime
    updated_at: datetime
    uptime_percent: float | None = None

    model_config = {"from_attributes": True}


class ServiceCheckResponse(BaseModel):
    id: int
    service_id: int
    status: str
    response_time_ms: float | None = None
    status_code: int | None = None
    error: str | None = None
    checked_at: datetime

    model_config = {"from_attributes": True}


class ServiceCheckReport(BaseModel):
    service_id: int
    status: str  # up / down
    response_time_ms: float | None = None
    status_code: int | None = None
    error: str | None = None
    checked_at: datetime | None = None
