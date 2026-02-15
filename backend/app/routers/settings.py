from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.setting import Setting
from app.models.user import User

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "metrics_retention_days": {"value": "90", "description": "指标数据保留天数"},
    "alert_check_interval": {"value": "60", "description": "告警检查间隔(秒)"},
    "heartbeat_timeout": {"value": "120", "description": "心跳超时时间(秒)"},
    "webhook_retry_count": {"value": "3", "description": "Webhook 重试次数"},
}


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Setting))
    settings = {s.key: {"value": s.value, "description": s.description} for s in result.scalars().all()}
    # Merge defaults
    for key, default in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default
    return settings


@router.put("")
async def update_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    for key, value in data.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            desc = DEFAULT_SETTINGS.get(key, {}).get("description", "")
            db.add(Setting(key=key, value=str(value), description=desc))
    await db.commit()
    return {"status": "ok"}
