"""
通知分发服务 (Notification Distribution Service)

功能描述 (Description):
    VigilOps 统一通知分发引擎，负责将告警和修复结果通知发送到多个渠道。
    实现智能降噪机制，避免告警风暴对运维人员造成干扰。
    
支持的通知渠道 (Supported Channels):
    1. Webhook - 通用HTTP接口，支持自定义headers
    2. Email - SMTP邮件发送，支持HTML模板
    3. DingTalk - 钉钉机器人，支持签名验证
    4. Feishu - 飞书机器人，支持富文本卡片
    5. WeCom - 企业微信机器人，支持Markdown格式
    
智能降噪特性 (Intelligent Noise Reduction):
    1. 静默时间窗口 (Silence Window) - 指定时间段内不发送通知
    2. 冷却时间控制 (Cooldown Control) - 同一规则的告警间隔发送
    3. 失败重试机制 (Retry Mechanism) - 网络异常时自动重试
    4. 通知模板系统 (Template System) - 支持自定义消息格式
    
技术特性 (Technical Features):
    - 异步发送：所有通知渠道支持并发发送
    - 容错设计：单个渠道失败不影响其他渠道
    - 状态跟踪：完整的发送日志和状态记录
    - 配置灵活：每个渠道独立配置和启用控制
"""
import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.alert import Alert, AlertRule
from app.models.notification import NotificationChannel, NotificationLog
from app.models.notification_template import NotificationTemplate

logger = logging.getLogger(__name__)

# 通知发送配置常量 (Notification Configuration Constants)
MAX_RETRIES = 3  # 发送失败时的最大重试次数，平衡可靠性和性能


# ---------------------------------------------------------------------------
# 自动修复结果通知模块 (Auto-Remediation Result Notification Module)
# 供 remediation agent 调用，通知修复执行结果
# ---------------------------------------------------------------------------

def _remediation_success_message(alert_name: str, host: str, runbook: str, duration: str) -> str:
    """
    修复成功通知正文生成器 (Remediation Success Message Generator)
    
    功能描述:
        生成自动修复成功时的通知消息，包含关键执行信息。
        
    Args:
        alert_name: 原始告警名称
        host: 执行修复的目标主机
        runbook: 执行的修复脚本名称
        duration: 修复执行耗时
        
    Returns:
        格式化的Markdown通知消息
    """
    return (
        f"✅ **自动修复成功**\n\n"
        f"**告警**: {alert_name}\n"
        f"**主机**: {host}\n"
        f"**Runbook**: {runbook}\n"
        f"**执行耗时**: {duration}"
    )


def _remediation_failure_message(alert_name: str, host: str, reason: str) -> str:
    """
    修复失败通知正文生成器 (Remediation Failure Message Generator)
    
    功能描述:
        生成自动修复失败时的告警升级消息，提醒人工介入。
        
    Args:
        alert_name: 原始告警名称
        host: 修复失败的目标主机
        reason: 失败原因描述
        
    Returns:
        格式化的紧急通知消息，提醒运维人员及时处理
    """
    return (
        f"❌ **自动修复失败，需人工介入**\n\n"
        f"**告警**: {alert_name}\n"
        f"**主机**: {host}\n"
        f"**失败原因**: {reason}"
    )


def _remediation_approval_message(alert_name: str, host: str, action: str, approval_url: str) -> str:
    """
    修复审批通知正文生成器 (Remediation Approval Message Generator)
    
    功能描述:
        生成需要人工审批的修复操作通知，提供审批链接。
        用于高风险操作的安全控制。
        
    Args:
        alert_name: 原始告警名称  
        host: 目标主机
        action: 建议执行的修复操作描述
        approval_url: 审批操作的Web界面链接
        
    Returns:
        包含审批链接的通知消息
    """
    return (
        f"🔒 **修复操作待审批**\n\n"
        f"**告警**: {alert_name}\n"
        f"**主机**: {host}\n"
        f"**建议操作**: {action}\n"
        f"**审批链接**: {approval_url}"
    )


async def send_remediation_notification(
    db: AsyncSession,
    *,
    kind: str,
    alert_name: str,
    host: str,
    runbook: str = "",
    duration: str = "",
    reason: str = "",
    action: str = "",
    approval_url: str = "",
) -> None:
    """
    修复结果统一通知接口 (Unified Remediation Notification Interface)
    
    功能描述:
        自动修复系统的通知入口，根据修复结果类型发送不同格式的通知。
        支持修复成功、失败、需审批三种场景的通知。
        
    Args:
        db: 数据库会话
        kind: 通知类型 - "success"(成功) | "failure"(失败) | "approval"(待审批)
        alert_name: 原始告警名称
        host: 目标主机标识
        runbook: 可选，执行的修复脚本名称（成功时使用）
        duration: 可选，修复执行耗时（成功时使用）
        reason: 可选，失败原因（失败时使用）
        action: 可选，建议操作描述（审批时使用）
        approval_url: 可选，审批链接（审批时使用）
        
    流程步骤:
        1. 根据kind类型选择对应的消息模板
        2. 查询所有已启用的通知渠道
        3. 并发向所有渠道发送通知
        4. 失败渠道记录异常，不影响其他渠道
    """
    # 1. 根据修复结果类型生成对应的通知正文
    if kind == "success":
        body = _remediation_success_message(alert_name, host, runbook, duration)
    elif kind == "approval":
        body = _remediation_approval_message(alert_name, host, action, approval_url)
    else:  # "failure" 或其他情况
        body = _remediation_failure_message(alert_name, host, reason)

    # 2. 查询所有已启用的通知渠道
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)  # noqa: E712
    )
    channels = result.scalars().all()

    # 3. 并发向所有渠道发送修复结果通知
    for channel in channels:
        try:
            await _send_remediation_to_channel(channel, body)
        except Exception:
            # 4. 容错处理：单个渠道失败不影响其他渠道
            logger.exception("Failed to send remediation notification to channel %s", channel.name)


async def _send_remediation_to_channel(channel: NotificationChannel, body: str) -> None:
    """复用现有渠道发送纯文本修复通知。"""
    config = channel.config

    if channel.type == "webhook":
        url = config.get("url", "")
        if not url:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"text": body}, headers={"Content-Type": "application/json"})

    elif channel.type == "dingtalk":
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return
        secret = config.get("secret")
        if secret:
            ts, sign = _dingtalk_sign(secret)
            sep = "&" if "?" in webhook_url else "?"
            webhook_url = f"{webhook_url}{sep}timestamp={ts}&sign={sign}"
        payload = {"msgtype": "markdown", "markdown": {"title": "VigilOps 修复通知", "text": body}}
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json=payload)

    elif channel.type == "feishu":
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return
        payload: dict = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": "VigilOps 修复通知"}, "template": "blue"},
                "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body}}],
            },
        }
        secret = config.get("secret")
        if secret:
            ts, sign = _feishu_sign(secret)
            payload["timestamp"] = ts
            payload["sign"] = sign
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json=payload)

    elif channel.type == "wecom":
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return
        payload = {"msgtype": "markdown", "markdown": {"content": body}}
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json=payload)

    elif channel.type == "email":
        import aiosmtplib
        smtp_host = config.get("smtp_host", "")
        smtp_port = config.get("smtp_port", 465)
        smtp_user = config.get("smtp_user", "")
        smtp_password = config.get("smtp_password", "")
        use_ssl = config.get("smtp_ssl", True)
        recipients = config.get("recipients", [])
        if not recipients:
            return
        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_user
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = "VigilOps 修复通知"
        msg.attach(MIMEText(body, "plain", "utf-8"))
        kwargs = {"hostname": smtp_host, "port": smtp_port, "username": smtp_user, "password": smtp_password}
        if use_ssl:
            kwargs["use_tls"] = True
        else:
            kwargs["start_tls"] = True
        await aiosmtplib.send(msg, **kwargs)


# ---------------------------------------------------------------------------
# 通知模板处理模块 (Notification Template Processing Module)  
# 负责模板变量提取、模板查找和内容渲染
# ---------------------------------------------------------------------------

def _build_template_vars(alert: Alert) -> dict:
    """
    告警模板变量构建器 (Alert Template Variables Builder)
    
    功能描述:
        从告警对象中提取关键字段，构建模板渲染所需的变量字典。
        处理空值和类型转换，确保模板渲染的稳定性。
        
    Args:
        alert: 告警对象，包含所有告警相关信息
        
    Returns:
        dict: 模板变量字典，包含格式化后的告警字段
        
    变量说明:
        - title: 告警标题
        - severity: 严重级别（critical/warning/info）
        - message: 详细告警消息
        - metric_value: 触发告警的指标值
        - threshold: 告警阈值
        - host_id: 告警来源主机ID
        - fired_at: 告警触发时间（格式化字符串）
    """
    return {
        "title": alert.title or "",                              # 告警标题，空值处理
        "severity": alert.severity or "",                        # 严重级别
        "message": alert.message or "",                          # 告警消息
        "metric_value": alert.metric_value if alert.metric_value is not None else "",  # 指标值，处理None
        "threshold": alert.threshold if alert.threshold is not None else "",            # 阈值，处理None
        "host_id": alert.host_id if alert.host_id is not None else "",                  # 主机ID，处理None
        "fired_at": alert.fired_at.strftime("%Y-%m-%d %H:%M:%S") if alert.fired_at else "",  # 时间格式化
    }


async def _get_default_template(db: AsyncSession, channel_type: str):
    """
    默认通知模板查找器 (Default Notification Template Finder)
    
    功能描述:
        按优先级查找指定渠道类型的默认通知模板。
        实现模板继承机制，支持通用模板作为后备。
        
    Args:
        db: 数据库会话
        channel_type: 渠道类型（webhook/email/dingtalk/feishu/wecom）
        
    Returns:
        NotificationTemplate对象或None
        
    查找策略:
        1. 优先查找精确匹配的渠道类型默认模板
        2. 未找到时回退到"all"类型的通用默认模板
        3. 支持模板继承和复用机制
    """
    # 1. 精确匹配查找：特定渠道类型的默认模板
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.channel_type == channel_type,
            NotificationTemplate.is_default == True,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if template:
        return template  # 找到精确匹配的模板，优先使用

    # 2. 回退查找：通用"all"类型的默认模板
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.channel_type == "all",
            NotificationTemplate.is_default == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()  # 返回通用模板或None


def _render_template(template, variables: dict) -> tuple[str | None, str]:
    """
    模板渲染引擎 (Template Rendering Engine)
    
    功能描述:
        使用Python字符串格式化语法渲染通知模板。
        支持主题和正文模板的独立渲染，容错处理变量缺失。
        
    Args:
        template: 通知模板对象，包含subject_template和body_template字段
        variables: 模板变量字典，包含{title}、{severity}等占位符对应值
        
    Returns:
        tuple: (subject, body) 元组
            - subject: 渲染后的主题（可能为None，如邮件以外渠道）
            - body: 渲染后的正文内容
            
    容错机制:
        - 变量缺失时使用原始模板内容
        - 格式化异常时保持模板不变
        - 确保渲染过程不会因数据问题中断
    """
    subject = None
    # 1. 主题模板渲染（主要用于邮件渠道）
    if template.subject_template:
        try:
            subject = template.subject_template.format(**variables)
        except (KeyError, IndexError):
            # 变量缺失或格式错误时，保持原始模板
            subject = template.subject_template

    # 2. 正文模板渲染（所有渠道必需）
    try:
        body = template.body_template.format(**variables)
    except (KeyError, IndexError):
        # 变量缺失或格式错误时，保持原始模板
        body = template.body_template

    return subject, body


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------

async def send_alert_notification(db: AsyncSession, alert: Alert):
    """
    告警通知智能分发引擎 (Intelligent Alert Notification Distribution Engine)
    
    功能描述:
        VigilOps 核心降噪引擎，实现智能化的告警通知分发。
        通过静默时间窗口和冷却时间控制，有效避免告警风暴。
        
    Args:
        db: 数据库会话，用于查询告警规则和通知渠道配置
        alert: 待发送通知的告警对象，包含触发信息和关联规则
        
    智能降噪流程 (Intelligent Noise Reduction Process):
        1. 静默窗口检查 (Silence Window Check) - 检查当前时间是否在静默期
        2. 冷却时间检查 (Cooldown Check) - 检查同规则告警是否在冷却期
        3. 多渠道并发发送 (Multi-channel Concurrent Send) - 向所有启用渠道发送
        4. 冷却期设置 (Cooldown Setup) - 发送后设置冷却标记防止重复通知
        
    降噪机制说明 (Noise Reduction Mechanisms):
        - 静默期 (Silence Period): 指定时间段内完全禁止发送通知
        - 冷却期 (Cooldown Period): 同一规则的告警在指定时间内只发送一次
        - 计数器 (Counter): 记录冷却期内被抑制的告警数量供统计分析
    """
    # 1. 告警规则配置获取 (Alert Rule Configuration Retrieval)
    # 查询关联的告警规则，获取降噪参数配置
    rule_result = await db.execute(select(AlertRule).where(AlertRule.id == alert.rule_id))
    rule = rule_result.scalar_one_or_none()

    # 2. 静默时间窗口检查 (Silence Window Check) - 降噪机制第一层
    # 在指定的静默时间段内，完全禁止发送任何通知
    if rule and rule.silence_start and rule.silence_end:
        now_time = datetime.now().time()  # 获取当前时间（仅时分秒）
        
        # 2.1 处理同日静默窗口（如 09:00-18:00）
        if rule.silence_start <= rule.silence_end:
            if rule.silence_start <= now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return  # 静默期内，直接返回不发送通知
        # 2.2 处理跨日静默窗口（如 23:00-07:00）
        else:
            if now_time >= rule.silence_start or now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return  # 跨日静默期内，直接返回

    # 3. 冷却时间检查 (Cooldown Check) - 降噪机制第二层  
    # 防止相同规则的告警短时间内重复发送，避免告警风暴
    redis = await get_redis()
    cooldown = rule.cooldown_seconds if rule else 300  # 默认5分钟冷却期
    cooldown_key = f"alert:cooldown:{alert.rule_id}"  # Redis键：按规则ID隔离
    
    if await redis.get(cooldown_key):
        # 3.1 冷却期内：增加抑制计数器，记录被过滤的告警数量
        await redis.incr(f"alert:cooldown:count:{alert.rule_id}")
        logger.info(f"Alert {alert.id} suppressed by cooldown")
        return  # 冷却期内，直接返回不发送通知

    # 4. 多渠道并发通知发送 (Multi-channel Concurrent Notification)
    # 通过降噪检查后，向所有启用的通知渠道发送告警
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)  # noqa: E712
    )
    channels = result.scalars().all()

    # 4.1 并发向所有已启用渠道发送通知
    for channel in channels:
        await _send_to_channel(db, alert, channel)  # 每个渠道独立处理，失败不互相影响

    # 5. 冷却期设置 (Cooldown Setup) - 发送后立即设置冷却标记
    # 防止后续相同规则的告警在冷却期内重复发送
    if cooldown > 0:
        # 5.1 设置冷却期标记，TTL为冷却时间（秒）
        await redis.setex(cooldown_key, cooldown, "1")
        # 5.2 清空冷却期计数器，为下一个冷却周期准备
        await redis.delete(f"alert:cooldown:count:{alert.rule_id}")


async def _send_to_channel(db: AsyncSession, alert: Alert, channel: NotificationChannel):
    """
    单渠道告警发送处理器 (Single Channel Alert Sender)
    
    功能描述:
        负责向指定的单个通知渠道发送告警，包含模板渲染、重试机制、状态记录。
        采用策略模式根据渠道类型分发到对应的发送函数。
        
    Args:
        db: 数据库会话
        alert: 告警对象
        channel: 目标通知渠道配置
        
    处理流程:
        1. 渠道类型分发到对应处理函数
        2. 查找并应用通知模板
        3. 执行带重试的发送逻辑
        4. 记录发送状态和日志
    """
    # 1. 渠道类型分发器 (Channel Type Dispatcher) - 策略模式实现
    dispatchers = {
        "webhook": _send_webhook,      # 通用Webhook发送
        "email": _send_email,          # SMTP邮件发送
        "dingtalk": _send_dingtalk,    # 钉钉机器人发送
        "feishu": _send_feishu,        # 飞书机器人发送
        "wecom": _send_wecom,          # 企业微信机器人发送
    }
    handler = dispatchers.get(channel.type)
    if not handler:
        logger.warning(f"不支持的通知渠道类型: {channel.type}")
        return

    # 2. 通知模板处理 (Notification Template Processing)
    template = await _get_default_template(db, channel.type)  # 查找渠道默认模板
    variables = _build_template_vars(alert)                   # 构建模板变量字典

    # 3. 初始化通知发送日志记录 (Initialize Notification Log)
    log = NotificationLog(
        alert_id=alert.id,
        channel_id=channel.id,
        status="failed",    # 默认失败，成功后更新
        retries=0,
    )

    # 4. 带重试机制的发送循环 (Retry-enabled Send Loop)
    # 网络异常、服务暂时不可用等情况的容错处理
    for attempt in range(MAX_RETRIES):
        try:
            # 4.1 调用对应渠道的发送函数
            resp_code = await handler(alert, channel, template, variables)
            log.response_code = resp_code
            
            # 4.2 检查HTTP状态码判断是否发送成功
            if resp_code and 200 <= resp_code < 300:
                log.status = "sent"
                break  # 发送成功，跳出重试循环
            log.error = f"HTTP {resp_code}"
        except Exception as e:
            # 4.3 捕获异常信息，限制长度避免日志过大
            log.error = str(e)[:500]
        log.retries = attempt + 1  # 记录重试次数

    # 5. 记录发送状态到数据库 (Record Send Status to Database)
    log.sent_at = datetime.now(timezone.utc)
    db.add(log)
    await db.commit()

    # 6. 发送结果日志记录 (Send Result Logging)
    if log.status == "sent":
        logger.info(f"Notification sent for alert {alert.id} to channel {channel.name}")
    else:
        logger.warning(f"Notification failed for alert {alert.id} to channel {channel.name}: {log.error}")


# ---------------------------------------------------------------------------
# Webhook 发送（保持原有逻辑）
# ---------------------------------------------------------------------------

async def _send_webhook(
    alert: Alert, channel: NotificationChannel, template, variables: dict
) -> int | None:
    """发送 Webhook 通知，保持向后兼容的原有逻辑。"""
    url = channel.config.get("url")
    if not url:
        return None

    headers = channel.config.get("headers", {})
    headers.setdefault("Content-Type", "application/json")

    # 如果有模板，使用模板渲染 body；否则使用原始 JSON
    if template:
        _, body = _render_template(template, variables)
        payload = {"text": body}
    else:
        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity,
            "status": alert.status,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "host_id": alert.host_id,
            "service_id": alert.service_id,
            "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
    return resp.status_code


# ---------------------------------------------------------------------------
# 邮件发送
# ---------------------------------------------------------------------------

async def _send_email(
    alert: Alert, channel: NotificationChannel, template, variables: dict
) -> int | None:
    """通过 SMTP 发送邮件通知。"""
    import aiosmtplib

    config = channel.config
    smtp_host = config.get("smtp_host", "")
    smtp_port = config.get("smtp_port", 465)
    smtp_user = config.get("smtp_user", "")
    smtp_password = config.get("smtp_password", "")
    use_ssl = config.get("smtp_ssl", True)
    recipients = config.get("recipients", [])

    if not recipients:
        logger.warning("邮件通知渠道未配置收件人")
        return None

    # 渲染内容
    if template:
        subject, body = _render_template(template, variables)
        if not subject:
            subject = f"[VigilOps 告警] {alert.severity} - {alert.title}"
    else:
        subject = f"[VigilOps 告警] {alert.severity} - {alert.title}"
        body = _default_email_html(variables)

    # 构建邮件
    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))

    # 发送
    kwargs = {
        "hostname": smtp_host,
        "port": smtp_port,
        "username": smtp_user,
        "password": smtp_password,
    }
    if use_ssl:
        kwargs["use_tls"] = True
    else:
        kwargs["start_tls"] = True

    await aiosmtplib.send(msg, **kwargs)
    return 200  # SMTP 无 HTTP 状态码，成功即返回 200


def _default_email_html(variables: dict) -> str:
    """生成默认的告警邮件 HTML 正文。"""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">
      <div style="background:#d32f2f;color:#fff;padding:16px 24px;">
        <h2 style="margin:0;">⚠️ VigilOps 告警通知</h2>
      </div>
      <div style="padding:24px;">
        <table style="width:100%;border-collapse:collapse;">
          <tr><td style="padding:8px 0;font-weight:bold;">标题</td><td>{variables['title']}</td></tr>
          <tr><td style="padding:8px 0;font-weight:bold;">严重级别</td><td>{variables['severity']}</td></tr>
          <tr><td style="padding:8px 0;font-weight:bold;">消息</td><td>{variables['message']}</td></tr>
          <tr><td style="padding:8px 0;font-weight:bold;">指标值</td><td>{variables['metric_value']}</td></tr>
          <tr><td style="padding:8px 0;font-weight:bold;">阈值</td><td>{variables['threshold']}</td></tr>
          <tr><td style="padding:8px 0;font-weight:bold;">主机 ID</td><td>{variables['host_id']}</td></tr>
          <tr><td style="padding:8px 0;font-weight:bold;">触发时间</td><td>{variables['fired_at']}</td></tr>
        </table>
      </div>
      <div style="background:#f5f5f5;padding:12px 24px;text-align:center;color:#888;font-size:12px;">
        VigilOps 监控平台
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# 钉钉机器人通知模块 (DingTalk Bot Notification Module)
# 实现钉钉Webhook签名验证和消息发送
# ---------------------------------------------------------------------------

def _dingtalk_sign(secret: str) -> tuple[str, str]:
    """
    钉钉Webhook签名计算器 (DingTalk Webhook Signature Calculator)
    
    功能描述:
        按照钉钉官方文档实现Webhook签名算法，确保消息安全性。
        使用HMAC-SHA256算法对时间戳和密钥进行签名。
        
    Args:
        secret: 钉钉机器人的加签密钥
        
    Returns:
        tuple: (timestamp, sign) 时间戳和签名字符串
        
    签名算法:
        1. 获取当前毫秒时间戳
        2. 构建待签名字符串：timestamp + "\n" + secret
        3. 使用HMAC-SHA256计算签名
        4. Base64编码后URL转义
        
    安全说明:
        签名机制防止恶意请求，确保只有拥有密钥的应用能发送消息
    """
    # 1. 获取当前毫秒级时间戳（钉钉要求毫秒精度）
    timestamp = str(int(time.time() * 1000))
    
    # 2. 构建待签名字符串（钉钉官方格式）
    string_to_sign = f"{timestamp}\n{secret}"
    
    # 3. HMAC-SHA256签名计算
    hmac_code = hmac.new(
        secret.encode("utf-8"), 
        string_to_sign.encode("utf-8"), 
        digestmod=hashlib.sha256
    ).digest()
    
    # 4. Base64编码并URL转义（符合钉钉API要求）
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode())
    
    return timestamp, sign


async def _send_dingtalk(
    alert: Alert, channel: NotificationChannel, template, variables: dict
) -> int | None:
    """发送钉钉机器人 Webhook 通知（markdown 格式）。"""
    config = channel.config
    webhook_url = config.get("webhook_url", "")
    secret = config.get("secret")

    if not webhook_url:
        return None

    # 签名
    if secret:
        ts, sign = _dingtalk_sign(secret)
        sep = "&" if "?" in webhook_url else "?"
        webhook_url = f"{webhook_url}{sep}timestamp={ts}&sign={sign}"

    # 渲染内容
    if template:
        _, body = _render_template(template, variables)
    else:
        body = (
            f"## ⚠️ VigilOps 告警\n\n"
            f"**标题**: {variables['title']}\n\n"
            f"**级别**: {variables['severity']}\n\n"
            f"**消息**: {variables['message']}\n\n"
            f"**触发时间**: {variables['fired_at']}"
        )

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"[告警] {variables['title']}",
            "text": body,
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json=payload)
    return resp.status_code


# ---------------------------------------------------------------------------
# 飞书机器人通知模块 (Feishu Bot Notification Module)
# 实现飞书Webhook签名验证和富文本卡片消息发送
# ---------------------------------------------------------------------------

def _feishu_sign(secret: str) -> tuple[str, str]:
    """
    飞书Webhook签名计算器 (Feishu Webhook Signature Calculator)
    
    功能描述:
        实现飞书官方Webhook签名算法，与钉钉略有差异。
        使用秒级时间戳和HMAC-SHA256算法进行签名。
        
    Args:
        secret: 飞书机器人的加签密钥
        
    Returns:
        tuple: (timestamp, sign) 时间戳和签名字符串
        
    签名算法差异:
        - 飞书使用秒级时间戳（与钉钉的毫秒级不同）
        - HMAC签名后直接Base64编码（无需URL转义）
        - 签名字符串格式与钉钉相同：timestamp + "\n" + secret
        
    注意事项:
        飞书签名算法参数顺序与标准HMAC不同，需特别注意
    """
    # 1. 获取当前秒级时间戳（飞书使用秒精度，与钉钉不同）
    timestamp = str(int(time.time()))
    
    # 2. 构建待签名字符串（与钉钉格式相同）
    string_to_sign = f"{timestamp}\n{secret}"
    
    # 3. HMAC-SHA256签名计算（注意：飞书的参数顺序特殊）
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),  # 飞书：待签名字符串作为key
        digestmod=hashlib.sha256
    ).digest()
    
    # 4. Base64编码（无需URL转义，与钉钉不同）
    sign = base64.b64encode(hmac_code).decode()
    
    return timestamp, sign


async def _send_feishu(
    alert: Alert, channel: NotificationChannel, template, variables: dict
) -> int | None:
    """发送飞书机器人 Webhook 通知（富文本卡片格式）。"""
    config = channel.config
    webhook_url = config.get("webhook_url", "")
    secret = config.get("secret")

    if not webhook_url:
        return None

    # 渲染内容
    if template:
        _, body = _render_template(template, variables)
    else:
        body = (
            f"**标题**: {variables['title']}\n"
            f"**级别**: {variables['severity']}\n"
            f"**消息**: {variables['message']}\n"
            f"**触发时间**: {variables['fired_at']}"
        )

    payload: dict = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "⚠️ VigilOps 告警"},
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": body},
                }
            ],
        },
    }

    # 签名
    if secret:
        ts, sign = _feishu_sign(secret)
        payload["timestamp"] = ts
        payload["sign"] = sign

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json=payload)
    return resp.status_code


# ---------------------------------------------------------------------------
# 企业微信发送
# ---------------------------------------------------------------------------

async def _send_wecom(
    alert: Alert, channel: NotificationChannel, template, variables: dict
) -> int | None:
    """发送企业微信机器人 Webhook 通知（markdown 格式）。"""
    config = channel.config
    webhook_url = config.get("webhook_url", "")

    if not webhook_url:
        return None

    # 渲染内容
    if template:
        _, body = _render_template(template, variables)
    else:
        body = (
            f"## <font color='warning'>⚠️ VigilOps 告警</font>\n"
            f"> **标题**: {variables['title']}\n"
            f"> **级别**: {variables['severity']}\n"
            f"> **消息**: {variables['message']}\n"
            f"> **触发时间**: {variables['fired_at']}"
        )

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": body},
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json=payload)
    return resp.status_code
