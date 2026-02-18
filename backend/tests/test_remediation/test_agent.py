"""Agent 集成测试：mock AI + dry-run 模式下完整流程。"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.remediation.agent import RemediationAgent
from app.remediation.ai_client import RemediationAIClient
from app.remediation.command_executor import CommandExecutor
from app.remediation.models import (
    Diagnosis,
    RemediationAlert,
    RiskLevel,
)
from app.remediation.runbook_registry import RunbookRegistry


def _mock_db():
    """创建 mock AsyncSession。"""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_alert(**kwargs) -> RemediationAlert:
    defaults = dict(
        alert_id=1,
        alert_type="disk_full",
        severity="warning",
        host="web-01",
        message="Disk usage at 95%",
    )
    defaults.update(kwargs)
    return RemediationAlert(**defaults)


@pytest.mark.asyncio
async def test_handle_alert_auto_dry_run():
    """AUTO 风险 + dry-run 模式下应该成功执行（不真正执行命令）。"""
    mock_diagnosis = Diagnosis(
        root_cause="Disk full due to old temp files",
        confidence=0.95,
        suggested_runbook="disk_cleanup",
    )
    ai = RemediationAIClient(mock_responses=[mock_diagnosis])
    executor = CommandExecutor(dry_run=True)
    agent = RemediationAgent(ai_client=ai, executor=executor)
    db = _mock_db()

    alert = _make_alert()
    result = await agent.handle_alert(alert, db)

    assert result.success is True
    assert result.runbook_name == "disk_cleanup"
    assert result.risk_level == RiskLevel.AUTO
    assert len(result.command_results) > 0
    assert all(not r.executed for r in result.command_results)  # dry-run
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_handle_alert_confirm_escalates():
    """CONFIRM 风险应该升级而不是执行。"""
    mock_diagnosis = Diagnosis(
        root_cause="Service crashed",
        confidence=0.9,
        suggested_runbook="service_restart",
    )
    ai = RemediationAIClient(mock_responses=[mock_diagnosis])
    agent = RemediationAgent(ai_client=ai)
    db = _mock_db()

    alert = _make_alert(alert_type="service_down", message="nginx is down")
    result = await agent.handle_alert(alert, db)

    assert result.success is False
    assert result.escalated is True
    assert "confirm" in result.blocked_reason.lower()


@pytest.mark.asyncio
async def test_handle_alert_no_runbook():
    """找不到 runbook 时应该升级。"""
    mock_diagnosis = Diagnosis(
        root_cause="Unknown issue",
        confidence=0.5,
        suggested_runbook="nonexistent_runbook",
    )
    ai = RemediationAIClient(mock_responses=[mock_diagnosis])
    agent = RemediationAgent(ai_client=ai)
    db = _mock_db()

    alert = _make_alert(alert_type="unknown_alert_type")
    result = await agent.handle_alert(alert, db)

    assert result.success is False
    assert result.escalated is True
    assert "no matching runbook" in result.blocked_reason.lower()


@pytest.mark.asyncio
async def test_circuit_breaker_blocks():
    """熔断器开启时应该直接拒绝。"""
    mock_diagnosis = Diagnosis(root_cause="test", confidence=0.9, suggested_runbook="disk_cleanup")
    ai = RemediationAIClient(mock_responses=[mock_diagnosis])
    agent = RemediationAgent(ai_client=ai)
    # 触发熔断
    for _ in range(3):
        agent.circuit_breaker.record_failure("web-01")
    db = _mock_db()

    alert = _make_alert()
    result = await agent.handle_alert(alert, db)

    assert result.success is False
    assert "circuit breaker" in result.blocked_reason.lower()


@pytest.mark.asyncio
async def test_runbook_registry_match():
    """Runbook 注册表应该正确匹配。"""
    registry = RunbookRegistry()
    assert len(registry.list_all()) == 6

    alert = _make_alert(alert_type="disk_full")
    diag = Diagnosis(root_cause="disk full", confidence=0.9, suggested_runbook="disk_cleanup")
    rb = registry.match(alert, diag)
    assert rb is not None
    assert rb.name == "disk_cleanup"
