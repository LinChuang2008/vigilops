"""
告警去重和聚合 API (Alert Deduplication and Aggregation API)

提供告警去重和聚合的配置管理和统计查看接口，包括：
- 查看/设置去重和聚合配置参数
- 查看去重和聚合统计信息
- 管理告警聚合组
- 清理过期记录

Provides configuration management and statistics APIs for alert deduplication and aggregation.
"""
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.alert_group import AlertGroup
from app.services.alert_deduplication import AlertDeduplicationService

router = APIRouter()


class DeduplicationConfigRequest(BaseModel):
    """去重配置请求模型"""
    deduplication_window_seconds: int = Field(ge=60, le=3600, description="去重时间窗口（秒，60-3600）")
    aggregation_window_seconds: int = Field(ge=300, le=7200, description="聚合时间窗口（秒，300-7200）")
    max_alerts_per_group: int = Field(ge=5, le=200, description="每个聚合组最大告警数（5-200）")


class DeduplicationConfigResponse(BaseModel):
    """去重配置响应模型"""
    deduplication_window_seconds: int
    aggregation_window_seconds: int
    max_alerts_per_group: int


class DeduplicationStatsResponse(BaseModel):
    """去重统计响应模型"""
    active_dedup_records: int = Field(description="活跃去重记录数")
    active_alert_groups: int = Field(description="活跃告警组数")
    deduplication_rate_24h: float = Field(description="24小时去重率（%）")
    suppressed_alerts_24h: int = Field(description="24小时抑制告警数")
    total_alert_occurrences_24h: int = Field(description="24小时总告警次数")


class AlertGroupSummary(BaseModel):
    """告警组摘要模型"""
    id: int
    title: str
    severity: str
    status: str
    alert_count: int
    rule_count: int = Field(description="涉及规则数")
    host_count: int = Field(description="涉及主机数")
    service_count: int = Field(description="涉及服务数")
    last_occurrence: str
    window_end: str


class AlertGroupListResponse(BaseModel):
    """告警组列表响应模型"""
    groups: List[AlertGroupSummary]
    total: int


@router.get("/config", response_model=DeduplicationConfigResponse)
def get_deduplication_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取告警去重和聚合配置
    
    Returns:
        DeduplicationConfigResponse: 当前配置
    """
    try:
        service = AlertDeduplicationService(db)
        
        config = {
            "deduplication_window_seconds": service.get_config("alert_deduplication_window_seconds", 300),
            "aggregation_window_seconds": service.get_config("alert_aggregation_window_seconds", 600),
            "max_alerts_per_group": service.get_config("alert_max_alerts_per_group", 50)
        }
        
        return DeduplicationConfigResponse(**config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取去重配置失败: {str(e)}")


@router.put("/config", response_model=DeduplicationConfigResponse)
def update_deduplication_config(
    config: DeduplicationConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新告警去重和聚合配置
    
    Args:
        config: 新的配置
        
    Returns:
        DeduplicationConfigResponse: 更新后的配置
    """
    try:
        # 检查用户权限（只有管理员可以修改）
        if current_user.role not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="只有管理员可以修改告警去重配置")
        
        service = AlertDeduplicationService(db)
        
        # 更新配置
        service.set_config(
            "alert_deduplication_window_seconds", 
            config.deduplication_window_seconds,
            "告警去重时间窗口（秒）"
        )
        service.set_config(
            "alert_aggregation_window_seconds",
            config.aggregation_window_seconds,
            "告警聚合时间窗口（秒）"
        )
        service.set_config(
            "alert_max_alerts_per_group",
            config.max_alerts_per_group,
            "每个聚合组最大告警数"
        )
        
        return DeduplicationConfigResponse(
            deduplication_window_seconds=config.deduplication_window_seconds,
            aggregation_window_seconds=config.aggregation_window_seconds,
            max_alerts_per_group=config.max_alerts_per_group
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新去重配置失败: {str(e)}")


@router.get("/statistics", response_model=DeduplicationStatsResponse)
def get_deduplication_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取告警去重和聚合统计信息
    
    Returns:
        DeduplicationStatsResponse: 统计信息
    """
    try:
        service = AlertDeduplicationService(db)
        stats = service.get_deduplication_statistics()
        
        return DeduplicationStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取去重统计失败: {str(e)}")


@router.get("/groups", response_model=AlertGroupListResponse)
def list_alert_groups(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取告警聚合组列表
    
    Args:
        status: 过滤状态 (firing/resolved/acknowledged)
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        AlertGroupListResponse: 告警组列表
    """
    try:
        query = db.query(AlertGroup)
        
        # 状态过滤
        if status:
            query = query.filter(AlertGroup.status == status)
        
        # 按最后发生时间倒序
        query = query.order_by(AlertGroup.last_occurrence.desc())
        
        # 分页
        total = query.count()
        groups = query.offset(offset).limit(limit).all()
        
        # 转换为响应模型
        group_summaries = []
        for group in groups:
            summary = AlertGroupSummary(
                id=group.id,
                title=group.title,
                severity=group.severity,
                status=group.status,
                alert_count=group.alert_count,
                rule_count=len(group.rule_ids or []),
                host_count=len(group.host_ids or []),
                service_count=len(group.service_ids or []),
                last_occurrence=group.last_occurrence.isoformat(),
                window_end=group.window_end.isoformat()
            )
            group_summaries.append(summary)
        
        return AlertGroupListResponse(groups=group_summaries, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警组列表失败: {str(e)}")


@router.post("/cleanup")
def cleanup_expired_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    清理过期的去重和聚合记录
    
    Returns:
        Dict: 清理统计结果
    """
    try:
        # 检查用户权限（只有管理员可以清理）
        if current_user.role not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="只有管理员可以清理过期记录")
        
        service = AlertDeduplicationService(db)
        cleanup_stats = service.cleanup_expired_records()
        
        return {
            "success": True,
            "message": "过期记录清理完成",
            "statistics": cleanup_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理过期记录失败: {str(e)}")


@router.patch("/groups/{group_id}/status")
def update_alert_group_status(
    group_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新告警组状态
    
    Args:
        group_id: 告警组 ID
        status: 新状态 (firing/resolved/acknowledged)
        
    Returns:
        Dict: 操作结果
    """
    try:
        if status not in ["firing", "resolved", "acknowledged"]:
            raise HTTPException(status_code=400, detail="无效的状态值")
        
        group = db.query(AlertGroup).filter(AlertGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="告警组不存在")
        
        group.status = status
        db.commit()
        
        return {
            "success": True,
            "message": f"告警组状态已更新为 {status}",
            "group_id": group_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新告警组状态失败: {str(e)}")


# 健康检查接口
@router.get("/health")
def health_check():
    """告警去重服务健康检查"""
    return {"status": "healthy", "service": "alert_deduplication"}