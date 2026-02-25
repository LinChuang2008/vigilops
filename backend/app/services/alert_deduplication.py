"""
告警去重和聚合服务 (Alert Deduplication and Aggregation Service)

实现智能告警去重和聚合逻辑，防止告警风暴，提升运维效率。
支持基于时间窗口、相似性规则、主机/服务等维度的告警管理。

Implements intelligent alert deduplication and aggregation logic to prevent
alert storms and improve operational efficiency. Supports alert management
based on time windows, similarity rules, and host/service dimensions.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertRule
from app.models.alert_group import AlertGroup, AlertDeduplication
from app.models.setting import Setting

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_DEDUPLICATION_WINDOW = 300  # 去重窗口：5分钟
DEFAULT_AGGREGATION_WINDOW = 600    # 聚合窗口：10分钟
DEFAULT_MAX_ALERTS_PER_GROUP = 50   # 每个聚合组最多告警数

# 配置键名
DEDUP_WINDOW_KEY = "alert_deduplication_window_seconds"
AGGREGATION_WINDOW_KEY = "alert_aggregation_window_seconds"
MAX_ALERTS_PER_GROUP_KEY = "alert_max_alerts_per_group"


class AlertDeduplicationService:
    """告警去重和聚合服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_config(self, key: str, default_value: int) -> int:
        """获取配置值"""
        try:
            setting = self.db.query(Setting).filter(Setting.key == key).first()
            if setting:
                return int(setting.value)
            return default_value
        except (ValueError, TypeError):
            return default_value

    def set_config(self, key: str, value: int, description: str) -> None:
        """设置配置值"""
        setting = self.db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(key=key, value=str(value), description=description)
            self.db.add(setting)
        self.db.commit()

    def generate_alert_fingerprint(self, rule_id: int, host_id: Optional[int], 
                                   service_id: Optional[int], metric: str) -> str:
        """
        生成告警指纹，用于去重判断
        
        Args:
            rule_id: 告警规则 ID
            host_id: 主机 ID  
            service_id: 服务 ID
            metric: 监控指标名
            
        Returns:
            str: 告警指纹哈希值
        """
        # 创建唯一标识符
        identifier = f"{rule_id}:{host_id or 'none'}:{service_id or 'none'}:{metric}"
        return hashlib.md5(identifier.encode()).hexdigest()

    def generate_group_key(self, rule_name: str, severity: str, 
                          host_ids: List[int], service_ids: List[int]) -> str:
        """
        生成告警组键，用于聚合判断
        
        Args:
            rule_name: 规则名称
            severity: 严重程度
            host_ids: 相关主机 ID 列表
            service_ids: 相关服务 ID 列表
            
        Returns:
            str: 告警组键
        """
        # 按相似性聚合：相同规则名前缀 + 相同严重程度
        rule_prefix = rule_name.split(' - ')[0] if ' - ' in rule_name else rule_name
        
        # 如果涉及少量主机（<=3），按主机聚合；否则按规则聚合
        if len(host_ids) <= 3:
            hosts_part = ','.join(map(str, sorted(host_ids)))
            return f"{rule_prefix}:{severity}:hosts:{hosts_part}"
        else:
            return f"{rule_prefix}:{severity}:rule_based"

    def should_deduplicate_alert(self, fingerprint: str) -> Tuple[bool, Optional[AlertDeduplication]]:
        """
        检查是否应该去重
        
        Args:
            fingerprint: 告警指纹
            
        Returns:
            Tuple[bool, Optional[AlertDeduplication]]: (是否去重, 现有去重记录)
        """
        dedup_window = self.get_config(DEDUP_WINDOW_KEY, DEFAULT_DEDUPLICATION_WINDOW)
        cutoff_time = datetime.utcnow() - timedelta(seconds=dedup_window)

        # 查找近期的去重记录
        existing_dedup = self.db.query(AlertDeduplication).filter(
            and_(
                AlertDeduplication.fingerprint == fingerprint,
                AlertDeduplication.last_occurrence > cutoff_time
            )
        ).first()

        return existing_dedup is not None, existing_dedup

    def find_or_create_alert_group(self, group_key: str, rule_id: int, host_id: Optional[int],
                                   service_id: Optional[int], severity: str, title: str) -> AlertGroup:
        """
        查找或创建告警聚合组
        
        Args:
            group_key: 聚合组键
            rule_id: 规则 ID
            host_id: 主机 ID
            service_id: 服务 ID
            severity: 严重程度
            title: 告警标题
            
        Returns:
            AlertGroup: 告警聚合组
        """
        aggregation_window = self.get_config(AGGREGATION_WINDOW_KEY, DEFAULT_AGGREGATION_WINDOW)
        window_start = datetime.utcnow() - timedelta(seconds=aggregation_window)

        # 查找活跃的聚合组
        existing_group = self.db.query(AlertGroup).filter(
            and_(
                AlertGroup.group_key == group_key,
                AlertGroup.status.in_(["firing", "acknowledged"]),
                AlertGroup.window_end > window_start
            )
        ).first()

        if existing_group:
            # 更新现有组
            existing_group.last_occurrence = datetime.utcnow()
            existing_group.window_end = datetime.utcnow() + timedelta(seconds=aggregation_window)
            existing_group.alert_count += 1
            
            # 更新涉及的资源列表
            if rule_id not in (existing_group.rule_ids or []):
                rule_ids = list(existing_group.rule_ids or [])
                rule_ids.append(rule_id)
                existing_group.rule_ids = rule_ids
                
            if host_id and host_id not in (existing_group.host_ids or []):
                host_ids = list(existing_group.host_ids or [])
                host_ids.append(host_id)
                existing_group.host_ids = host_ids
                
            if service_id and service_id not in (existing_group.service_ids or []):
                service_ids = list(existing_group.service_ids or [])
                service_ids.append(service_id)
                existing_group.service_ids = service_ids

            # 提升严重程度（如果需要）
            severity_order = {"info": 1, "warning": 2, "critical": 3}
            current_level = severity_order.get(existing_group.severity, 1)
            new_level = severity_order.get(severity, 1)
            if new_level > current_level:
                existing_group.severity = severity

            self.db.commit()
            return existing_group
        else:
            # 创建新的聚合组
            new_group = AlertGroup(
                group_key=group_key,
                title=f"聚合告警: {title}",
                severity=severity,
                status="firing",
                alert_count=1,
                rule_ids=[rule_id],
                host_ids=[host_id] if host_id else [],
                service_ids=[service_id] if service_id else [],
                window_start=datetime.utcnow(),
                window_end=datetime.utcnow() + timedelta(seconds=aggregation_window),
                last_occurrence=datetime.utcnow()
            )
            self.db.add(new_group)
            self.db.flush()
            return new_group

    def process_alert_deduplication(self, rule: AlertRule, host_id: Optional[int], 
                                   service_id: Optional[int], metric_value: float,
                                   alert_title: str) -> Tuple[bool, Optional[str]]:
        """
        处理告警去重和聚合
        
        Args:
            rule: 告警规则
            host_id: 主机 ID
            service_id: 服务 ID  
            metric_value: 指标值
            alert_title: 告警标题
            
        Returns:
            Tuple[bool, Optional[str]]: (是否应该创建告警, 处理信息)
        """
        # 生成告警指纹
        fingerprint = self.generate_alert_fingerprint(rule.id, host_id, service_id, rule.metric)
        
        # 检查去重
        should_dedup, existing_dedup = self.should_deduplicate_alert(fingerprint)
        
        if should_dedup and existing_dedup:
            # 更新现有去重记录
            existing_dedup.last_occurrence = datetime.utcnow()
            existing_dedup.occurrence_count += 1
            self.db.commit()
            
            logger.info(f"Alert deduplicated: {alert_title} (count: {existing_dedup.occurrence_count})")
            return False, f"告警已去重，累计触发 {existing_dedup.occurrence_count} 次"

        # 生成聚合组键
        group_key = self.generate_group_key(
            rule.name, 
            rule.severity,
            [host_id] if host_id else [],
            [service_id] if service_id else []
        )

        # 查找或创建聚合组
        alert_group = self.find_or_create_alert_group(
            group_key, rule.id, host_id, service_id, rule.severity, alert_title
        )

        # 检查聚合组是否已达到最大告警数
        max_alerts = self.get_config(MAX_ALERTS_PER_GROUP_KEY, DEFAULT_MAX_ALERTS_PER_GROUP)
        if alert_group.alert_count > max_alerts:
            logger.warning(f"Alert group {group_key} exceeds max alerts ({max_alerts})")

        # 创建或更新去重记录
        if existing_dedup:
            existing_dedup.last_occurrence = datetime.utcnow()
            existing_dedup.occurrence_count += 1
            existing_dedup.alert_group_id = alert_group.id
        else:
            dedup_record = AlertDeduplication(
                fingerprint=fingerprint,
                rule_id=rule.id,
                host_id=host_id,
                service_id=service_id,
                first_occurrence=datetime.utcnow(),
                last_occurrence=datetime.utcnow(),
                occurrence_count=1,
                alert_group_id=alert_group.id
            )
            self.db.add(dedup_record)

        self.db.commit()

        # 对于聚合组中的第一个告警或每10个告警，允许创建个别告警
        if alert_group.alert_count == 1 or alert_group.alert_count % 10 == 0:
            return True, f"告警已聚合到组 {group_key}，当前组内共 {alert_group.alert_count} 个告警"
        else:
            return False, f"告警已聚合，组内共 {alert_group.alert_count} 个告警，暂不单独通知"

    def cleanup_expired_records(self) -> Dict[str, int]:
        """清理过期的去重和聚合记录"""
        dedup_window = self.get_config(DEDUP_WINDOW_KEY, DEFAULT_DEDUPLICATION_WINDOW)
        aggregation_window = self.get_config(AGGREGATION_WINDOW_KEY, DEFAULT_AGGREGATION_WINDOW)
        
        now = datetime.utcnow()
        dedup_cutoff = now - timedelta(seconds=dedup_window * 2)  # 保留时间更长一些
        aggregation_cutoff = now - timedelta(seconds=aggregation_window * 2)

        # 清理过期的去重记录
        expired_dedup_count = self.db.query(AlertDeduplication).filter(
            AlertDeduplication.last_occurrence < dedup_cutoff
        ).delete()

        # 清理过期的聚合组
        expired_group_count = self.db.query(AlertGroup).filter(
            and_(
                AlertGroup.window_end < aggregation_cutoff,
                AlertGroup.status.in_(["resolved"])
            )
        ).delete()

        self.db.commit()

        stats = {
            "expired_dedup_records": expired_dedup_count,
            "expired_alert_groups": expired_group_count
        }

        logger.info(f"Cleaned up expired alert records: {stats}")
        return stats

    def get_deduplication_statistics(self) -> Dict[str, any]:
        """获取去重和聚合统计信息"""
        # 活跃的去重记录数
        active_dedup_count = self.db.query(AlertDeduplication).filter(
            AlertDeduplication.last_occurrence > datetime.utcnow() - timedelta(hours=1)
        ).count()

        # 活跃的聚合组数
        active_group_count = self.db.query(AlertGroup).filter(
            AlertGroup.status.in_(["firing", "acknowledged"])
        ).count()

        # 去重率统计（最近24小时）
        yesterday = datetime.utcnow() - timedelta(hours=24)
        total_occurrences = self.db.query(AlertDeduplication).filter(
            AlertDeduplication.last_occurrence > yesterday
        ).count()

        suppressed_occurrences = sum(
            dedup.occurrence_count - 1 for dedup in 
            self.db.query(AlertDeduplication).filter(
                AlertDeduplication.last_occurrence > yesterday
            ).all()
        )

        dedup_rate = (suppressed_occurrences / total_occurrences * 100) if total_occurrences > 0 else 0

        return {
            "active_dedup_records": active_dedup_count,
            "active_alert_groups": active_group_count,
            "deduplication_rate_24h": round(dedup_rate, 2),
            "suppressed_alerts_24h": suppressed_occurrences,
            "total_alert_occurrences_24h": total_occurrences
        }