"""
数据保留策略 API (Data Retention Policy API)

提供数据保留策略的配置和管理接口，包括：
- 查看/设置各类型数据的保留天数
- 手动触发数据清理
- 查看数据统计和清理历史

Provides configuration and management APIs for data retention policies, including:
- View/set retention days for different data types
- Manually trigger data cleanup
- View data statistics and cleanup history
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.data_retention import DataRetentionService

router = APIRouter()


class RetentionSettingsRequest(BaseModel):
    """数据保留设置请求模型"""
    host_metrics: int = Field(ge=1, le=3650, description="主机指标保留天数 (1-3650天)")
    db_metrics: int = Field(ge=1, le=3650, description="数据库指标保留天数 (1-3650天)")
    log_entries: int = Field(ge=1, le=365, description="日志条目保留天数 (1-365天)")
    ai_insights: int = Field(ge=1, le=3650, description="AI洞察保留天数 (1-3650天)")
    audit_logs: int = Field(ge=1, le=3650, description="审计日志保留天数 (1-3650天)")


class RetentionSettingsResponse(BaseModel):
    """数据保留设置响应模型"""
    host_metrics: int
    db_metrics: int
    log_entries: int
    ai_insights: int
    audit_logs: int


class CleanupStatsResponse(BaseModel):
    """数据清理统计响应模型"""
    host_metrics: int = Field(description="清理的主机指标记录数")
    db_metrics: int = Field(description="清理的数据库指标记录数")
    log_entries: int = Field(description="清理的日志条目记录数")
    ai_insights: int = Field(description="清理的AI洞察记录数")
    audit_logs: int = Field(description="清理的审计日志记录数")
    total: int = Field(description="总清理记录数")


class DataStatsResponse(BaseModel):
    """数据统计响应模型"""
    host_metrics: Dict[str, int] = Field(description="主机指标统计")
    db_metrics: Dict[str, int] = Field(description="数据库指标统计")
    log_entries: Dict[str, int] = Field(description="日志条目统计")
    ai_insights: Dict[str, int] = Field(description="AI洞察统计")
    audit_logs: Dict[str, int] = Field(description="审计日志统计")


@router.get("/settings", response_model=RetentionSettingsResponse)
def get_retention_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前数据保留策略设置
    
    Returns:
        RetentionSettingsResponse: 各类型数据的保留天数
    """
    try:
        service = DataRetentionService(db)
        
        settings = {
            "host_metrics": service.get_retention_days("host_metrics"),
            "db_metrics": service.get_retention_days("db_metrics"),
            "log_entries": service.get_retention_days("log_entries"),
            "ai_insights": service.get_retention_days("ai_insights"),
            "audit_logs": service.get_retention_days("audit_logs")
        }
        
        return RetentionSettingsResponse(**settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取保留策略设置失败: {str(e)}")


@router.put("/settings", response_model=RetentionSettingsResponse)
def update_retention_settings(
    settings: RetentionSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新数据保留策略设置
    
    Args:
        settings: 新的保留策略设置
        
    Returns:
        RetentionSettingsResponse: 更新后的设置
    """
    try:
        # 检查用户权限（只有管理员可以修改）
        if current_user.role not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="只有管理员可以修改数据保留策略")
        
        service = DataRetentionService(db)
        
        # 更新各类型数据的保留天数
        service.set_retention_days("host_metrics", settings.host_metrics)
        service.set_retention_days("db_metrics", settings.db_metrics)
        service.set_retention_days("log_entries", settings.log_entries)
        service.set_retention_days("ai_insights", settings.ai_insights)
        service.set_retention_days("audit_logs", settings.audit_logs)
        
        # 返回更新后的设置
        return RetentionSettingsResponse(
            host_metrics=settings.host_metrics,
            db_metrics=settings.db_metrics,
            log_entries=settings.log_entries,
            ai_insights=settings.ai_insights,
            audit_logs=settings.audit_logs
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新保留策略设置失败: {str(e)}")


@router.post("/cleanup", response_model=CleanupStatsResponse)
def trigger_data_cleanup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动触发数据清理
    
    Returns:
        CleanupStatsResponse: 清理统计结果
    """
    try:
        # 检查用户权限（只有管理员可以手动清理）
        if current_user.role not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="只有管理员可以触发数据清理")
        
        service = DataRetentionService(db)
        cleanup_stats = service.cleanup_expired_data()
        
        total = sum(cleanup_stats.values())
        
        return CleanupStatsResponse(
            host_metrics=cleanup_stats.get("host_metrics", 0),
            db_metrics=cleanup_stats.get("db_metrics", 0),
            log_entries=cleanup_stats.get("log_entries", 0),
            ai_insights=cleanup_stats.get("ai_insights", 0),
            audit_logs=cleanup_stats.get("audit_logs", 0),
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据清理失败: {str(e)}")


@router.get("/statistics", response_model=DataStatsResponse)
def get_data_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据统计信息
    
    Returns:
        DataStatsResponse: 各类型数据的统计信息
    """
    try:
        service = DataRetentionService(db)
        stats = service.get_data_statistics()
        
        return DataStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据统计失败: {str(e)}")


# 健康检查接口
@router.get("/health")
def health_check():
    """数据保留策略服务健康检查"""
    return {"status": "healthy", "service": "data_retention"}