"""
运维报告生成服务

从数据库收集监控数据，调用 AI 生成 Markdown 格式的运维报告（日报/周报）。
"""
import logging
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.host import Host
from app.models.host_metric import HostMetric
from app.models.service import Service
from app.models.alert import Alert
from app.models.log_entry import LogEntry
from app.models.db_metric import MonitoredDatabase, DbMetric
from app.models.report import Report
from app.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)

# 报告生成的系统提示词
REPORT_SYSTEM_PROMPT = """你是 VigilOps 运维报告生成器。根据提供的监控数据，生成专业的运维报告。

报告格式要求：
1. 使用 Markdown 格式
2. 包含以下章节：概述、主机资源、服务可用性、告警分析、日志分析、数据库状态、总结与建议
3. 用数据说话，包含具体数字
4. 风险和异常用 ⚠️ 标注
5. 最后给出改进建议"""


async def _collect_host_summary(db: AsyncSession, start: datetime, end: datetime) -> str:
    """收集主机状态汇总数据。"""
    # 主机总数和状态分布
    host_result = await db.execute(select(Host.status, func.count(Host.id)).group_by(Host.status))
    host_stats = {row[0]: row[1] for row in host_result.all()}
    total_hosts = sum(host_stats.values())

    # 时间段内的平均指标
    metric_result = await db.execute(
        select(
            func.avg(HostMetric.cpu_percent),
            func.avg(HostMetric.memory_percent),
            func.avg(HostMetric.disk_percent),
            func.max(HostMetric.cpu_percent),
            func.max(HostMetric.memory_percent),
            func.max(HostMetric.disk_percent),
        ).where(and_(HostMetric.recorded_at >= start, HostMetric.recorded_at < end))
    )
    row = metric_result.one_or_none()

    lines = [
        f"主机总数: {total_hosts}",
        f"在线: {host_stats.get('online', 0)}, 离线: {host_stats.get('offline', 0)}",
    ]
    if row and row[0] is not None:
        lines.extend([
            f"平均 CPU: {row[0]:.1f}%, 峰值: {row[3]:.1f}%",
            f"平均内存: {row[1]:.1f}%, 峰值: {row[4]:.1f}%",
            f"平均磁盘: {row[2]:.1f}%, 峰值: {row[5]:.1f}%",
        ])
    else:
        lines.append("该时段无指标数据")

    return "\n".join(lines)


async def _collect_service_summary(db: AsyncSession) -> str:
    """收集服务可用性汇总。"""
    result = await db.execute(
        select(Service.status, func.count(Service.id)).group_by(Service.status)
    )
    stats = {row[0]: row[1] for row in result.all()}
    total = sum(stats.values())
    up = stats.get("up", 0)
    rate = (up / total * 100) if total > 0 else 0
    return f"服务总数: {total}, 正常: {up}, 异常: {total - up}, 可用率: {rate:.1f}%"


async def _collect_alert_summary(db: AsyncSession, start: datetime, end: datetime) -> str:
    """收集告警统计（按严重级别/状态分组）。"""
    # 按严重级别分组
    sev_result = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(and_(Alert.fired_at >= start, Alert.fired_at < end))
        .group_by(Alert.severity)
    )
    sev_stats = {row[0]: row[1] for row in sev_result.all()}

    # 按状态分组
    status_result = await db.execute(
        select(Alert.status, func.count(Alert.id))
        .where(and_(Alert.fired_at >= start, Alert.fired_at < end))
        .group_by(Alert.status)
    )
    status_stats = {row[0]: row[1] for row in status_result.all()}

    total = sum(sev_stats.values())
    lines = [f"告警总数: {total}"]
    if sev_stats:
        lines.append("按级别: " + ", ".join(f"{k}={v}" for k, v in sev_stats.items()))
    if status_stats:
        lines.append("按状态: " + ", ".join(f"{k}={v}" for k, v in status_stats.items()))
    return "\n".join(lines)


async def _collect_log_summary(db: AsyncSession, start: datetime, end: datetime) -> str:
    """收集错误日志统计（按 service 分组 Top 10）。"""
    result = await db.execute(
        select(LogEntry.service, func.count(LogEntry.id).label("cnt"))
        .where(and_(
            LogEntry.timestamp >= start,
            LogEntry.timestamp < end,
            LogEntry.level.in_(["ERROR", "CRITICAL", "error", "critical"]),
        ))
        .group_by(LogEntry.service)
        .order_by(func.count(LogEntry.id).desc())
        .limit(10)
    )
    rows = result.all()
    if not rows:
        return "该时段无错误日志"
    total_errors = sum(r[1] for r in rows)
    lines = [f"错误日志总数: {total_errors} (Top 10 服务):"]
    for svc, cnt in rows:
        lines.append(f"  {svc or '未知'}: {cnt} 条")
    return "\n".join(lines)


async def _collect_db_summary(db: AsyncSession) -> str:
    """收集数据库健康状况。"""
    result = await db.execute(select(MonitoredDatabase))
    dbs = result.scalars().all()
    if not dbs:
        return "未配置监控数据库"
    lines = [f"监控数据库数量: {len(dbs)}"]
    for d in dbs:
        lines.append(f"  {d.name} ({d.db_type}): {d.status}")
    return "\n".join(lines)


async def generate_report(
    db: AsyncSession,
    report_type: str,
    period_start: datetime,
    period_end: datetime,
    generated_by: int | None = None,
) -> Report:
    """生成运维报告的核心函数。

    Args:
        db: 数据库会话
        report_type: 报告类型 ("daily" / "weekly")
        period_start: 报告覆盖起始时间
        period_end: 报告覆盖结束时间
        generated_by: 触发用户 ID（定时任务为 None）

    Returns:
        生成的 Report 对象
    """
    # 构建标题
    if report_type == "daily":
        title = f"日报 {period_start.strftime('%Y-%m-%d')}"
    else:
        title = f"周报 {period_start.strftime('%Y-%m-%d')}~{period_end.strftime('%Y-%m-%d')}"

    # 创建报告记录（状态: generating）
    report = Report(
        title=title,
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        content="",
        summary="",
        status="generating",
        generated_by=generated_by,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    try:
        # 收集各维度数据
        host_summary = await _collect_host_summary(db, period_start, period_end)
        service_summary = await _collect_service_summary(db)
        alert_summary = await _collect_alert_summary(db, period_start, period_end)
        log_summary = await _collect_log_summary(db, period_start, period_end)
        db_summary = await _collect_db_summary(db)

        # 组装提示词
        type_label = "日报" if report_type == "daily" else "周报"
        user_prompt = (
            f"请生成 {period_start.strftime('%Y-%m-%d')} 至 {period_end.strftime('%Y-%m-%d')} 的运维{type_label}。\n\n"
            f"【主机资源】\n{host_summary}\n\n"
            f"【服务可用性】\n{service_summary}\n\n"
            f"【告警统计】\n{alert_summary}\n\n"
            f"【错误日志】\n{log_summary}\n\n"
            f"【数据库状态】\n{db_summary}\n\n"
            f"请生成完整的 Markdown 格式运维报告，并在最后给出一段不超过 100 字的摘要（用【摘要】标记）。"
        )

        messages = [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # 调用 AI 生成报告
        result_text = await ai_engine._call_api(messages)

        # 分离摘要和正文
        content = result_text
        summary = ""
        if "【摘要】" in result_text:
            parts = result_text.split("【摘要】", 1)
            content = parts[0].strip()
            summary = parts[1].strip()
        else:
            # 取前 100 字作为摘要
            summary = result_text[:100].replace("\n", " ") + "..."

        report.content = content
        report.summary = summary
        report.status = "completed"
        await db.commit()
        await db.refresh(report)
        logger.info("报告生成成功: %s (id=%d)", title, report.id)

    except Exception as e:
        logger.error("报告生成失败: %s", str(e))
        report.status = "failed"
        report.content = f"生成失败: {str(e)}"
        report.summary = f"生成失败: {str(e)}"
        await db.commit()
        await db.refresh(report)

    return report
