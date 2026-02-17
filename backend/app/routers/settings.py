"""系统设置管理路由模块。

提供系统配置项的读取和更新接口，仅管理员可修改设置。
未在数据库中的配置项会回退到默认值。
"""

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.setting import Setting
from app.models.user import User
from app.services.audit import log_audit

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

# 系统默认配置项及说明
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
    """获取所有系统设置，数据库中未配置的项使用默认值补充。"""
    result = await db.execute(select(Setting))
    settings = {s.key: {"value": s.value, "description": s.description} for s in result.scalars().all()}
    # 合并默认值：数据库中不存在的配置项使用默认值
    for key, default in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default
    return settings


@router.put("")
async def update_settings(
    data: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量更新系统设置，仅管理员可操作。"""
    if user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")

    for key, value in data.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            # 已存在则更新值
            setting.value = str(value)
        else:
            # 不存在则创建新配置项
            desc = DEFAULT_SETTINGS.get(key, {}).get("description", "")
            db.add(Setting(key=key, value=str(value), description=desc))

    await log_audit(db, user.id, "update_settings", "settings", None,
                    json.dumps(data),
                    request.client.host if request.client else None)
    await db.commit()
    return {"status": "ok"}
