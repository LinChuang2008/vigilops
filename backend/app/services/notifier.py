"""
通知分发服务模块。

负责将告警通知发送到所有已启用的通知渠道，
支持多渠道（Webhook / 邮件 / 钉钉 / 飞书 / 企业微信），
支持通知模板、静默窗口、冷却时间控制和失败重试机制。
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

# 发送最大重试次数
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# 模板相关辅助函数
# ---------------------------------------------------------------------------

def _build_template_vars(alert: Alert) -> dict:
    """从告警对象中提取模板变量字典。"""
    return {
        "title": alert.title or "",
        "severity": alert.severity or "",
        "message": alert.message or "",
        "metric_value": alert.metric_value if alert.metric_value is not None else "",
        "threshold": alert.threshold if alert.threshold is not None else "",
        "host_id": alert.host_id if alert.host_id is not None else "",
        "fired_at": alert.fired_at.strftime("%Y-%m-%d %H:%M:%S") if alert.fired_at else "",
    }


async def _get_default_template(db: AsyncSession, channel_type: str):
    """查找指定渠道类型（或 all 类型）的默认模板。"""
    # 优先查找精确匹配的渠道类型默认模板
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.channel_type == channel_type,
            NotificationTemplate.is_default == True,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if template:
        return template

    # 回退到 all 类型的默认模板
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.channel_type == "all",
            NotificationTemplate.is_default == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


def _render_template(template, variables: dict) -> tuple[str | None, str]:
    """渲染模板，返回 (subject, body)。subject 可能为 None。"""
    subject = None
    if template.subject_template:
        try:
            subject = template.subject_template.format(**variables)
        except (KeyError, IndexError):
            subject = template.subject_template

    try:
        body = template.body_template.format(**variables)
    except (KeyError, IndexError):
        body = template.body_template

    return subject, body


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------

async def send_alert_notification(db: AsyncSession, alert: Alert):
    """为告警发送通知到所有已启用的通知渠道。

    处理流程：静默窗口检查 → 冷却时间检查 → 发送通知 → 设置冷却。

    Args:
        db: 数据库会话
        alert: 需要发送通知的告警对象
    """
    # 1. 查询关联的告警规则，获取冷却和静默配置
    rule_result = await db.execute(select(AlertRule).where(AlertRule.id == alert.rule_id))
    rule = rule_result.scalar_one_or_none()

    # 2. 检查是否在静默时间窗口内
    if rule and rule.silence_start and rule.silence_end:
        now_time = datetime.now().time()
        if rule.silence_start <= rule.silence_end:
            if rule.silence_start <= now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return
        else:
            if now_time >= rule.silence_start or now_time <= rule.silence_end:
                logger.info(f"Alert {alert.id} silenced (current time in silence window)")
                return

    # 3. 检查冷却时间
    redis = await get_redis()
    cooldown = rule.cooldown_seconds if rule else 300
    cooldown_key = f"alert:cooldown:{alert.rule_id}"
    if await redis.get(cooldown_key):
        await redis.incr(f"alert:cooldown:count:{alert.rule_id}")
        logger.info(f"Alert {alert.id} suppressed by cooldown")
        return

    # 4. 向所有已启用的通知渠道发送通知
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.is_enabled == True)  # noqa: E712
    )
    channels = result.scalars().all()

    for channel in channels:
        await _send_to_channel(db, alert, channel)

    # 5. 发送完成后设置冷却标记
    if cooldown > 0:
        await redis.setex(cooldown_key, cooldown, "1")
        await redis.delete(f"alert:cooldown:count:{alert.rule_id}")


async def _send_to_channel(db: AsyncSession, alert: Alert, channel: NotificationChannel):
    """向单个通知渠道发送告警，根据渠道类型分发到不同发送函数。"""
    dispatchers = {
        "webhook": _send_webhook,
        "email": _send_email,
        "dingtalk": _send_dingtalk,
        "feishu": _send_feishu,
        "wecom": _send_wecom,
    }
    handler = dispatchers.get(channel.type)
    if not handler:
        logger.warning(f"不支持的通知渠道类型: {channel.type}")
        return

    # 查找默认模板
    template = await _get_default_template(db, channel.type)
    variables = _build_template_vars(alert)

    # 创建通知日志记录
    log = NotificationLog(
        alert_id=alert.id,
        channel_id=channel.id,
        status="failed",
        retries=0,
    )

    # 带重试的发送逻辑
    for attempt in range(MAX_RETRIES):
        try:
            resp_code = await handler(alert, channel, template, variables)
            log.response_code = resp_code
            if resp_code and 200 <= resp_code < 300:
                log.status = "sent"
                break
            log.error = f"HTTP {resp_code}"
        except Exception as e:
            log.error = str(e)[:500]
        log.retries = attempt + 1

    log.sent_at = datetime.now(timezone.utc)
    db.add(log)
    await db.commit()

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
# 钉钉签名计算与发送
# ---------------------------------------------------------------------------

def _dingtalk_sign(secret: str) -> tuple[str, str]:
    """计算钉钉 Webhook 签名，返回 (timestamp, sign)。"""
    timestamp = str(int(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
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
# 飞书签名计算与发送
# ---------------------------------------------------------------------------

def _feishu_sign(secret: str) -> tuple[str, str]:
    """计算飞书 Webhook 签名，返回 (timestamp, sign)。"""
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
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
