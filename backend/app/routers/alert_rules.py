"""告警规则管理路由模块。

提供告警规则的增删改查 CRUD 接口，支持按启用状态筛选。
内置规则不允许删除。
"""

from typing import Optional, List

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.alert import AlertRule
from app.models.user import User
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse
from app.services.audit import log_audit

router = APIRouter(prefix="/api/v1/alert-rules", tags=["alert-rules"])


@router.get("", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    is_enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取告警规则列表，可按启用状态筛选。"""
    q = select(AlertRule).order_by(AlertRule.id)
    if is_enabled is not None:
        q = q.where(AlertRule.is_enabled == is_enabled)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    data: AlertRuleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """创建自定义告警规则。"""
    rule = AlertRule(**data.model_dump(), is_builtin=False)
    db.add(rule)
    await db.flush()
    await log_audit(db, _user.id, "create_alert_rule", "alert_rule", rule.id,
                    json.dumps(data.model_dump()),
                    request.client.host if request.client else None)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """根据 ID 获取单条告警规则。"""
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """更新指定告警规则，仅更新请求中包含的字段。"""
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rule, field, value)

    await log_audit(db, _user.id, "update_alert_rule", "alert_rule", rule_id,
                    json.dumps(updates),
                    request.client.host if request.client else None)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """删除指定告警规则，内置规则禁止删除。"""
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    if rule.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in rule")

    await log_audit(db, _user.id, "delete_alert_rule", "alert_rule", rule_id,
                    None, request.client.host if request.client else None)
    await db.delete(rule)
    await db.commit()
