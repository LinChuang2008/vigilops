"""
告警升级引擎 (Alert Escalation Engine)

提供告警自动升级的核心逻辑，包括升级条件检查、升级执行、通知增强等功能。
定期扫描需要升级的告警，并按配置的规则自动执行升级操作。

Provides core logic for automatic alert escalation, including escalation condition checking,
execution, and enhanced notifications. Periodically scans alerts that need escalation.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertRule
from app.models.escalation import EscalationRule, AlertEscalation
from app.services.notifier import send_alert_notification


logger = logging.getLogger(__name__)


class EscalationEngine:
    """告警升级引擎类 (Alert Escalation Engine Class)"""

    @staticmethod
    async def scan_and_escalate_alerts(db: AsyncSession) -> dict:
        """
        扫描并执行告警升级 (Scan and Execute Alert Escalation)
        
        扫描所有需要升级的告警，并按配置的升级规则执行自动升级。
        
        Args:
            db: 数据库会话
        Returns:
            dict: 升级执行结果统计
        """
        logger.info("开始扫描需要升级的告警")
        
        # 查找需要升级的告警
        pending_alerts = await EscalationEngine._find_alerts_for_escalation(db)
        escalated_count = 0
        failed_count = 0
        
        for alert in pending_alerts:
            try:
                success = await EscalationEngine._execute_alert_escalation(db, alert)
                if success:
                    escalated_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"升级告警 {alert.id} 时发生错误: {str(e)}")
                failed_count += 1
        
        await db.commit()
        
        result = {
            "scanned_alerts": len(pending_alerts),
            "escalated_count": escalated_count,
            "failed_count": failed_count,
            "scan_time": datetime.now(timezone.utc)
        }
        
        logger.info(f"告警升级扫描完成: {result}")
        return result

    @staticmethod
    async def _find_alerts_for_escalation(db: AsyncSession) -> List[Alert]:
        """
        查找需要升级的告警 (Find Alerts for Escalation)
        
        查找满足升级条件的告警：状态为firing或acknowledged，且已到达下次升级时间。
        
        Args:
            db: 数据库会话
        Returns:
            List[Alert]: 需要升级的告警列表
        """
        now = datetime.now(timezone.utc)
        
        query = select(Alert).where(
            and_(
                Alert.status.in_(["firing", "acknowledged"]),  # 只升级未解决的告警
                Alert.next_escalation_at <= now,  # 已到达升级时间
                Alert.next_escalation_at.isnot(None)  # 设置了升级时间
            )
        )
        
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def _execute_alert_escalation(db: AsyncSession, alert: Alert) -> bool:
        """
        执行单个告警的升级 (Execute Single Alert Escalation)
        
        对单个告警执行升级操作，包括更新严重程度、记录升级历史、发送通知。
        
        Args:
            db: 数据库会话
            alert: 要升级的告警
        Returns:
            bool: 升级是否成功
        """
        try:
            # 查找告警规则和升级规则
            escalation_rule = await EscalationEngine._get_escalation_rule(db, alert.rule_id)
            if not escalation_rule:
                logger.warning(f"告警 {alert.id} 没有配置升级规则")
                # 清除升级时间，避免重复扫描
                alert.next_escalation_at = None
                return False
            
            # 确定下一个升级级别
            next_level = alert.escalation_level + 1
            escalation_config = EscalationEngine._get_escalation_level_config(
                escalation_rule.escalation_levels, next_level
            )
            
            if not escalation_config:
                logger.info(f"告警 {alert.id} 已达到最高升级级别")
                alert.next_escalation_at = None
                return False
            
            # 记录原严重程度
            original_severity = alert.severity
            
            # 执行升级
            alert.severity = escalation_config["severity"]
            alert.escalation_level = next_level
            alert.last_escalated_at = datetime.now(timezone.utc)
            
            # 设置下次升级时间（如果还有下一级）
            next_config = EscalationEngine._get_escalation_level_config(
                escalation_rule.escalation_levels, next_level + 1
            )
            if next_config:
                alert.next_escalation_at = datetime.now(timezone.utc) + timedelta(
                    minutes=next_config["delay_minutes"]
                )
            else:
                alert.next_escalation_at = None
            
            # 记录升级历史
            escalation_record = AlertEscalation(
                alert_id=alert.id,
                escalation_rule_id=escalation_rule.id,
                from_severity=original_severity,
                to_severity=alert.severity,
                escalation_level=next_level,
                escalated_by_system=True,
                message=f"自动升级到级别 {next_level}: {original_severity} → {alert.severity}"
            )
            db.add(escalation_record)
            
            # 发送升级通知
            await EscalationEngine._send_escalation_notification(db, alert, escalation_record)
            
            logger.info(f"成功升级告警 {alert.id}: {original_severity} → {alert.severity} (级别 {next_level})")
            return True
            
        except Exception as e:
            logger.error(f"升级告警 {alert.id} 时发生错误: {str(e)}")
            return False

    @staticmethod
    async def _get_escalation_rule(db: AsyncSession, alert_rule_id: int) -> Optional[EscalationRule]:
        """获取告警规则对应的升级规则 (Get Escalation Rule for Alert Rule)"""
        query = select(EscalationRule).where(
            and_(
                EscalationRule.alert_rule_id == alert_rule_id,
                EscalationRule.is_enabled == True
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _get_escalation_level_config(escalation_levels: List[Dict[str, Any]], level: int) -> Optional[Dict[str, Any]]:
        """获取指定升级级别的配置 (Get Configuration for Specific Escalation Level)"""
        for config in escalation_levels:
            if config.get("level") == level:
                return config
        return None

    @staticmethod
    async def _send_escalation_notification(db: AsyncSession, alert: Alert, escalation_record: AlertEscalation):
        """
        发送升级通知 (Send Escalation Notification)
        
        发送告警升级的通知，使用更紧急的通知方式。
        
        Args:
            db: 数据库会话
            alert: 升级的告警
            escalation_record: 升级记录
        """
        try:
            # 构造升级通知内容
            message = f"""
🔥 告警升级通知

告警已自动升级到级别 {escalation_record.escalation_level}
- 告警标题: {alert.title}
- 严重程度: {escalation_record.from_severity} → {escalation_record.to_severity}
- 升级时间: {escalation_record.escalated_at.strftime('%Y-%m-%d %H:%M:%S')}
- 升级原因: 告警未及时处理

请立即关注并处理此告警！
"""
            
            # 发送升级通知
            await send_alert_notification(db, alert)
            
        except Exception as e:
            logger.error(f"发送升级通知失败: {str(e)}")

    @staticmethod
    async def manual_escalate_alert(
        db: AsyncSession, 
        alert_id: int, 
        to_severity: str, 
        user_id: int,
        message: Optional[str] = None
    ) -> AlertEscalation:
        """
        手动升级告警 (Manual Alert Escalation)
        
        由用户手动执行告警升级操作。
        
        Args:
            db: 数据库会话
            alert_id: 告警ID
            to_severity: 目标严重程度
            user_id: 操作用户ID
            message: 升级原因
        Returns:
            AlertEscalation: 升级记录
        """
        # 获取告警信息
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert:
            raise ValueError(f"告警 {alert_id} 不存在")
        
        if alert.status == "resolved":
            raise ValueError("已解决的告警不能升级")
        
        # 记录原严重程度
        original_severity = alert.severity
        
        # 执行升级
        alert.severity = to_severity
        alert.escalation_level += 1
        alert.last_escalated_at = datetime.now(timezone.utc)
        # 手动升级后暂停自动升级
        alert.next_escalation_at = None
        
        # 记录升级历史
        escalation_record = AlertEscalation(
            alert_id=alert.id,
            escalation_rule_id=None,  # 手动升级没有规则
            from_severity=original_severity,
            to_severity=to_severity,
            escalation_level=alert.escalation_level,
            escalated_by_system=False,
            message=message or f"手动升级: {original_severity} → {to_severity}"
        )
        db.add(escalation_record)
        
        await db.commit()
        await db.refresh(escalation_record)
        
        logger.info(f"手动升级告警 {alert_id}: {original_severity} → {to_severity}")
        return escalation_record

    @staticmethod
    async def setup_alert_escalation(db: AsyncSession, alert: Alert, escalation_rule: EscalationRule):
        """
        为新告警设置升级计划 (Setup Escalation Schedule for New Alert)
        
        为新创建的告警设置升级时间表。
        
        Args:
            db: 数据库会话
            alert: 新创建的告警
            escalation_rule: 升级规则
        """
        if not escalation_rule or not escalation_rule.is_enabled:
            return
            
        # 获取第一级升级配置
        first_level_config = EscalationEngine._get_escalation_level_config(
            escalation_rule.escalation_levels, 1
        )
        
        if first_level_config:
            # 设置首次升级时间
            alert.next_escalation_at = datetime.now(timezone.utc) + timedelta(
                minutes=first_level_config["delay_minutes"]
            )
            
            logger.info(f"为告警 {alert.id} 设置升级计划，首次升级时间: {alert.next_escalation_at}")