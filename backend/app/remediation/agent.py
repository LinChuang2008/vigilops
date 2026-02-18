"""
RemediationAgent：核心编排器。

告警 → AI 诊断 → Runbook 匹配 → 安全检查 → 命令执行 → 验证 → 写入 DB。
~200 行逻辑，无框架依赖。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

UTC = timezone.utc
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.remediation_log import RemediationLog
from app.services.memory_client import memory_client
from app.services.notifier import send_remediation_notification
from .ai_client import RemediationAIClient
from .command_executor import CommandExecutor
from .models import (
    CommandResult,
    Diagnosis,
    RemediationAlert,
    RemediationResult,
    RiskLevel,
    RunbookDefinition,
    RunbookStep,
)
from .runbook_registry import RunbookRegistry
from .safety import CircuitBreaker, RateLimiter, assess_risk, check_command_safety

logger = logging.getLogger(__name__)


class RemediationAgent:
    """AI 驱动的自动修复 Agent。

    主流程：Alert → Diagnose → Match → Check → Execute → Verify → Persist。
    """

    def __init__(
        self,
        ai_client: RemediationAIClient,
        executor: Optional[CommandExecutor] = None,
        registry: Optional[RunbookRegistry] = None,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.ai = ai_client
        self.executor = executor or CommandExecutor(dry_run=True)
        self.registry = registry or RunbookRegistry()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    async def handle_alert(
        self,
        alert: RemediationAlert,
        db: AsyncSession,
        context: Optional[dict[str, Any]] = None,
        triggered_by: str = "auto",
    ) -> RemediationResult:
        """主入口：端到端处理一条告警，并将结果写入 DB。"""
        logger.info("Handling alert: %s", alert.summary())

        # 创建 DB 记录
        log = RemediationLog(
            alert_id=alert.alert_id,
            host_id=alert.host_id,
            status="diagnosing",
            triggered_by=triggered_by,
        )
        db.add(log)
        await db.flush()

        # Step 0: 熔断检查
        if self.circuit_breaker.is_open(alert.host):
            logger.warning("Circuit breaker OPEN for host %s", alert.host)
            result = RemediationResult(
                alert_id=alert.alert_id,
                success=False,
                blocked_reason=f"Circuit breaker open for host {alert.host}",
                escalated=True,
            )
            await self._update_log(db, log, result, alert)
            return result

        # Step 1: AI 诊断
        diagnosis = await self._diagnose(alert, context)

        # Step 2: 匹配 Runbook
        runbook = self.registry.match(alert, diagnosis)
        if not runbook:
            result = RemediationResult(
                alert_id=alert.alert_id,
                success=False,
                diagnosis=diagnosis,
                blocked_reason="No matching runbook found",
                escalated=True,
            )
            await self._update_log(db, log, result, alert)
            return result

        # Step 3: 风险评估
        recent_count = self.rate_limiter.recent_count(alert.host)
        risk = assess_risk(runbook, diagnosis, recent_count)

        # Step 4: 限流检查
        if not self.rate_limiter.can_execute(
            alert.host, runbook.name, runbook.cooldown_seconds
        ):
            result = RemediationResult(
                alert_id=alert.alert_id,
                success=False,
                runbook_name=runbook.name,
                diagnosis=diagnosis,
                risk_level=risk,
                blocked_reason=f"Rate limited: {runbook.name} on {alert.host}",
                escalated=True,
            )
            await self._update_log(db, log, result, alert)
            return result

        # Step 5: 根据风险执行或升级
        if risk == RiskLevel.BLOCK:
            result = RemediationResult(
                alert_id=alert.alert_id,
                success=False,
                runbook_name=runbook.name,
                diagnosis=diagnosis,
                risk_level=risk,
                blocked_reason="Risk assessment: BLOCK",
                escalated=True,
            )
            await self._update_log(db, log, result, alert)
            return result

        if risk == RiskLevel.CONFIRM:
            result = RemediationResult(
                alert_id=alert.alert_id,
                success=False,
                runbook_name=runbook.name,
                diagnosis=diagnosis,
                risk_level=risk,
                blocked_reason="Needs human confirmation (risk=confirm)",
                escalated=True,
            )
            log.status = "pending_approval"
            await self._update_log(db, log, result, alert)
            return result

        # risk == AUTO → 执行
        log.status = "executing"
        await db.flush()

        result = await self._execute_runbook(alert, diagnosis, runbook, risk)
        await self._update_log(db, log, result, alert)
        return result

    async def _diagnose(
        self, alert: RemediationAlert, context: Optional[dict[str, Any]]
    ) -> Diagnosis:
        try:
            diagnosis = await self.ai.diagnose(alert, context or {})
            logger.info(
                "Diagnosis: cause=%s, confidence=%.2f, suggested=%s",
                diagnosis.root_cause, diagnosis.confidence, diagnosis.suggested_runbook,
            )
            return diagnosis
        except Exception as e:
            logger.error("Diagnosis failed: %s", e)
            return Diagnosis(root_cause="Diagnosis error", confidence=0.0, reasoning=str(e))

    async def _execute_runbook(
        self,
        alert: RemediationAlert,
        diagnosis: Diagnosis,
        runbook: RunbookDefinition,
        risk: RiskLevel,
    ) -> RemediationResult:
        logger.info("Executing runbook: %s on %s", runbook.name, alert.host)

        for step in runbook.commands:
            resolved_cmd = self._resolve_command(step.command, alert)
            is_safe, reason = check_command_safety(resolved_cmd)
            if not is_safe:
                return RemediationResult(
                    alert_id=alert.alert_id,
                    success=False,
                    runbook_name=runbook.name,
                    diagnosis=diagnosis,
                    risk_level=risk,
                    blocked_reason=f"Unsafe command: {reason}",
                    escalated=True,
                )

        resolved_steps = [
            RunbookStep(
                description=s.description,
                command=self._resolve_command(s.command, alert),
                timeout_seconds=s.timeout_seconds,
            )
            for s in runbook.commands
        ]
        command_results = await self.executor.execute_steps(resolved_steps)

        any_failure = any(r.exit_code != 0 for r in command_results)

        verification_passed: bool | None = None
        if not any_failure and runbook.verify_commands:
            resolved_verify = [
                RunbookStep(
                    description=s.description,
                    command=self._resolve_command(s.command, alert),
                    timeout_seconds=s.timeout_seconds,
                )
                for s in runbook.verify_commands
            ]
            verify_results = await self.executor.execute_steps(resolved_verify)
            command_results.extend(verify_results)
            verification_passed = all(r.exit_code == 0 for r in verify_results)

        self.rate_limiter.record_execution(alert.host, runbook.name)

        success = not any_failure and (verification_passed is not False)
        if success:
            self.circuit_breaker.record_success(alert.host)
        else:
            self.circuit_breaker.record_failure(alert.host)

        return RemediationResult(
            alert_id=alert.alert_id,
            success=success,
            runbook_name=runbook.name,
            diagnosis=diagnosis,
            risk_level=risk,
            command_results=command_results,
            verification_passed=verification_passed,
        )

    def _resolve_command(self, command: str, alert: RemediationAlert) -> str:
        resolved = command.replace("{host}", alert.host)
        for key, value in alert.labels.items():
            resolved = resolved.replace(f"{{{key}}}", value)
        return resolved

    async def _update_log(
        self, db: AsyncSession, log: RemediationLog, result: RemediationResult,
        alert: RemediationAlert | None = None,
    ) -> None:
        """将修复结果写回 DB 记录，并发送通知。"""
        if result.success:
            log.status = "success"
        elif result.escalated:
            if log.status != "pending_approval":
                log.status = "escalated"
        else:
            log.status = "failed"

        log.runbook_name = result.runbook_name
        log.risk_level = result.risk_level.value if result.risk_level else None
        log.diagnosis_json = result.diagnosis.model_dump() if result.diagnosis else None
        log.command_results_json = [r.model_dump() for r in result.command_results] if result.command_results else None
        log.verification_passed = result.verification_passed
        log.blocked_reason = result.blocked_reason
        log.completed_at = datetime.now(UTC)

        await db.commit()

        # --- 异步存储修复经验到记忆系统（不阻塞主流程） ---
        self._store_remediation_experience(log, result, alert)

        # --- 发送修复结果通知 ---
        await self._notify_result(db, log, result, alert)

    def _store_remediation_experience(
        self, log: RemediationLog, result: RemediationResult,
        alert: RemediationAlert | None,
    ) -> None:
        """将修复经验异步存储到记忆系统，不阻塞主流程。"""
        alert_name = alert.title if alert else "unknown"
        host = alert.host if alert else "unknown"
        status = log.status or "unknown"
        root_cause = result.diagnosis.root_cause if result.diagnosis else "N/A"
        runbook = result.runbook_name or "N/A"

        content = (
            f"修复经验 [{status}]: 告警={alert_name}, 主机={host}\n"
            f"根因: {root_cause}\n"
            f"Runbook: {runbook}\n"
            f"结果: {'成功' if result.success else '失败/升级'}"
        )
        if result.blocked_reason:
            content += f"\n原因: {result.blocked_reason}"

        try:
            asyncio.create_task(memory_client.store(content, source="vigilops-remediation"))
        except Exception:
            logger.debug("Failed to schedule remediation experience storage")

    async def _notify_result(
        self, db: AsyncSession, log: RemediationLog, result: RemediationResult,
        alert: RemediationAlert | None,
    ) -> None:
        """根据配置发送修复结果通知，复用现有通知通道。"""
        alert_name = alert.title if alert else (result.runbook_name or "unknown")
        host = alert.host if alert else "unknown"

        try:
            if result.success and settings.agent_notify_on_success:
                duration = ""
                if log.completed_at and log.created_at:
                    delta = log.completed_at - log.created_at
                    duration = f"{delta.total_seconds():.1f}s"
                await send_remediation_notification(
                    db, kind="success", alert_name=alert_name, host=host,
                    runbook=result.runbook_name or "", duration=duration,
                )
            elif log.status == "pending_approval" and settings.agent_notify_on_failure:
                await send_remediation_notification(
                    db, kind="approval", alert_name=alert_name, host=host,
                    action=result.blocked_reason or "",
                    approval_url=f"/remediation/{log.id}/approve",
                )
            elif not result.success and settings.agent_notify_on_failure:
                await send_remediation_notification(
                    db, kind="failure", alert_name=alert_name, host=host,
                    reason=result.blocked_reason or "unknown error",
                )
        except Exception:
            logger.exception("Failed to send remediation notification")
