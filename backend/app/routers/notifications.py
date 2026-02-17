"""通知渠道管理路由模块。

提供通知渠道（邮件、Webhook 等）的增删改查接口，
以及通知发送日志的查询功能。
"""

from typing import Optional, List

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.notification import NotificationChannel, NotificationLog
from app.models.user import User
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
    NotificationLogResponse,
)

router = APIRouter(prefix="/api/v1/notification-channels", tags=["notifications"])


@router.get("/logs", response_model=List[NotificationLogResponse])
async def list_notification_logs(
    alert_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """查询通知发送日志，可按告警 ID 筛选。"""
    q = select(NotificationLog).order_by(NotificationLog.sent_at.desc())
    if alert_id:
        q = q.where(NotificationLog.alert_id == alert_id)
    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("", response_model=List[NotificationChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取所有通知渠道列表。"""
    result = await db.execute(select(NotificationChannel).order_by(NotificationChannel.id))
    return result.scalars().all()


@router.post("", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: NotificationChannelCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """创建新的通知渠道。"""
    from app.services.audit import log_audit
    channel = NotificationChannel(**data.model_dump())
    db.add(channel)
    await db.flush()
    await log_audit(db, _user.id, "create_notification_channel", "notification_channel", channel.id,
                    json.dumps(data.model_dump()),
                    request.client.host if request.client else None)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.put("/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(
    channel_id: int,
    data: NotificationChannelUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """更新指定通知渠道配置。"""
    from app.services.audit import log_audit
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(channel, field, value)

    await log_audit(db, _user.id, "update_notification_channel", "notification_channel", channel_id,
                    json.dumps(updates),
                    request.client.host if request.client else None)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """删除指定通知渠道。"""
    from app.services.audit import log_audit
    result = await db.execute(select(NotificationChannel).where(NotificationChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await log_audit(db, _user.id, "delete_notification_channel", "notification_channel", channel_id,
                    None, request.client.host if request.client else None)
    await db.delete(channel)
    await db.commit()
