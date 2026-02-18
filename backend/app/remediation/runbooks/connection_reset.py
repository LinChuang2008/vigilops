"""Runbook：连接重置。处理连接耗尽问题。"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="connection_reset",
    description="Reset stale connections and identify connection leaks",
    match_alert_types=["too_many_connections", "connection_exhaustion", "connection_timeout", "port_exhaustion"],
    match_keywords=["connection", "too many", "exhaustion", "TIME_WAIT", "CLOSE_WAIT", "port"],
    risk_level=RiskLevel.CONFIRM,
    commands=[
        RunbookStep(description="Show connection states", command="ss -s", timeout_seconds=10),
        RunbookStep(description="List connections in TIME_WAIT state", command="ss -tan state time-wait | head -50", timeout_seconds=10),
        RunbookStep(description="List connections in CLOSE_WAIT state", command="ss -tan state close-wait | head -50", timeout_seconds=10),
        RunbookStep(description="Show processes with most connections", command="ss -tnp | awk '{print $6}' | sort | head -20", timeout_seconds=10),
    ],
    verify_commands=[
        RunbookStep(description="Verify connection count decreased", command="ss -s", timeout_seconds=10),
    ],
    cooldown_seconds=300,
)
