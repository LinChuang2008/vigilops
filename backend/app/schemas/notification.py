from datetime import datetime
from pydantic import BaseModel


class NotificationChannelCreate(BaseModel):
    name: str
    type: str = "webhook"
    config: dict  # {"url": "...", "headers": {...}}
    is_enabled: bool = True


class NotificationChannelUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    is_enabled: bool | None = None


class NotificationChannelResponse(BaseModel):
    id: int
    name: str
    type: str
    config: dict
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    id: int
    alert_id: int
    channel_id: int
    status: str
    response_code: int | None
    error: str | None
    retries: int
    sent_at: datetime

    model_config = {"from_attributes": True}
