"""
通知渠道管理路由模块 (Notification Channel Management Router)

功能说明：提供多渠道通知配置管理和发送日志查询功能
核心职责：
  - 通知渠道CRUD操作（支持邮件、钉钉、飞书、企微、Webhook）
  - 通知发送日志查询和审计
  - 渠道配置的安全存储和管理
  - 支持告警通知的多渠道分发
依赖关系：依赖SQLAlchemy、JWT认证、审计服务
API端点：GET /logs, GET /notification-channels, POST /notification-channels, PUT /notification-channels/{id}, DELETE /notification-channels/{id}

Author: VigilOps Team
"""

import logging
from typing import Optional, List

import json

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_operator_user
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
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    通知发送日志查询接口 (Notification Sending Logs Query)
    
    查询通知发送历史记录，支持多维度筛选和分页查询。
    
    Args:
        alert_id: 告警ID筛选
        channel_id: 通知渠道ID筛选  
        status: 发送状态筛选 (sent/failed)
        start_time: 开始时间 (ISO format)
        end_time: 结束时间 (ISO format)
        page: 页码 (从1开始)
        page_size: 每页条数
    """
    from datetime import datetime
    
    q = select(NotificationLog).order_by(NotificationLog.sent_at.desc())
    
    # 多维度过滤
    if alert_id:
        q = q.where(NotificationLog.alert_id == alert_id)
    if channel_id:
        q = q.where(NotificationLog.channel_id == channel_id)
    if status:
        q = q.where(NotificationLog.status == status)
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            q = q.where(NotificationLog.sent_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            q = q.where(NotificationLog.sent_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")
    
    # 分页
    offset = (page - 1) * page_size
    q = q.offset(offset).limit(page_size)
    
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/logs/stats")
async def get_notification_logs_stats(
    days: int = Query(7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    通知日志统计接口 (Notification Logs Statistics)
    
    获取指定天数内的通知发送统计信息。
    
    Args:
        days: 统计天数 (1-365)
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, case
    
    # 时间范围
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # 总体统计
    total_query = select(func.count(NotificationLog.id)).where(
        NotificationLog.sent_at >= start_time
    )
    total_result = await db.execute(total_query)
    total_notifications = total_result.scalar() or 0
    
    # 成功/失败统计
    success_query = select(func.count(NotificationLog.id)).where(
        and_(
            NotificationLog.sent_at >= start_time,
            NotificationLog.status == "sent"
        )
    )
    success_result = await db.execute(success_query)
    success_count = success_result.scalar() or 0
    
    failed_query = select(func.count(NotificationLog.id)).where(
        and_(
            NotificationLog.sent_at >= start_time,
            NotificationLog.status == "failed"
        )
    )
    failed_result = await db.execute(failed_query)
    failed_count = failed_result.scalar() or 0
    
    # 按渠道统计
    channel_stats_query = select(
        NotificationChannel.name,
        NotificationChannel.type,
        func.count(NotificationLog.id).label("count"),
        func.sum(
            case(
                (NotificationLog.status == "sent", 1),
                else_=0
            )
        ).label("success_count")
    ).select_from(
        NotificationLog.__table__.join(
            NotificationChannel.__table__,
            NotificationLog.channel_id == NotificationChannel.id
        )
    ).where(
        NotificationLog.sent_at >= start_time
    ).group_by(
        NotificationChannel.id, NotificationChannel.name, NotificationChannel.type
    )
    
    channel_result = await db.execute(channel_stats_query)
    channel_stats = [
        {
            "channel_name": row.name,
            "channel_type": row.type,
            "total_count": row.count,
            "success_count": row.success_count or 0,
            "success_rate": round(((row.success_count or 0) / row.count * 100) if row.count > 0 else 0, 2)
        }
        for row in channel_result
    ]
    
    # 成功率
    success_rate = round((success_count / total_notifications * 100) if total_notifications > 0 else 0, 2)
    
    return {
        "period_days": days,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_notifications": total_notifications,
        "success_count": success_count,
        "failed_count": failed_count,
        "success_rate": success_rate,
        "channel_statistics": channel_stats
    }


@router.post("/logs/{log_id}/retry")
async def retry_notification(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    重试失败的通知发送 (Retry Failed Notification)
    
    重新发送失败的通知，更新重试次数和状态。
    
    Args:
        log_id: 通知日志ID
    """
    # 查找通知日志
    log_query = select(NotificationLog).where(NotificationLog.id == log_id)
    log_result = await db.execute(log_query)
    notification_log = log_result.scalar_one_or_none()
    
    if not notification_log:
        raise HTTPException(status_code=404, detail="Notification log not found")
    
    if notification_log.status == "sent":
        raise HTTPException(status_code=400, detail="Cannot retry successful notification")
    
    # 检查重试次数限制
    if notification_log.retries >= 3:
        raise HTTPException(status_code=400, detail="Maximum retry attempts reached")
    
    try:
        # 获取告警和渠道信息
        from app.models.alert import Alert
        alert_query = select(Alert).where(Alert.id == notification_log.alert_id)
        alert_result = await db.execute(alert_query)
        alert = alert_result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Associated alert not found")
        
        channel_query = select(NotificationChannel).where(NotificationChannel.id == notification_log.channel_id)
        channel_result = await db.execute(channel_query)
        channel = channel_result.scalar_one_or_none()
        
        if not channel:
            raise HTTPException(status_code=404, detail="Associated channel not found")
        
        # 重新发送通知
        from app.services.notifier import send_alert_notification_to_channel
        success = await send_alert_notification_to_channel(alert, channel)
        
        # 更新重试记录
        notification_log.retries += 1
        if success:
            notification_log.status = "sent"
            notification_log.error = None
            notification_log.response_code = 200
        else:
            notification_log.error = "Retry failed"
            notification_log.response_code = 500
        
        notification_log.sent_at = datetime.utcnow()
        await db.commit()
        
        # 记录审计日志
        from app.services.audit import log_audit
        await log_audit(
            db,
            current_user.id,
            "retry_notification",
            "notification_log",
            log_id,
            f"Retried notification (attempt {notification_log.retries})"
        )
        
        return {
            "success": True,
            "message": f"Notification retry {'successful' if success else 'failed'}",
            "retry_count": notification_log.retries,
            "status": notification_log.status
        }
        
    except Exception as e:
        notification_log.retries += 1
        notification_log.error = str(e)
        notification_log.response_code = 500
        await db.commit()
        
        logger.error(f"Failed to retry notification {log_id}: {e}")
        return {
            "success": False,
            "message": f"Retry failed: {str(e)}",
            "retry_count": notification_log.retries,
            "status": notification_log.status
        }


@router.get("", response_model=List[NotificationChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    通知渠道列表查询接口 (Notification Channels List Query)
    
    获取所有配置的通知渠道（邮件、钉钉、飞书、企微、Webhook）。
    """
    result = await db.execute(select(NotificationChannel).order_by(NotificationChannel.id))
    return result.scalars().all()


@router.post("", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: NotificationChannelCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_operator_user),
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
