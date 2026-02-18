"""Runbook：服务重启。需要确认，因为重启会导致短暂中断。"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="service_restart",
    description="Restart a failed or unresponsive service",
    match_alert_types=["service_down", "service_unhealthy", "process_not_running"],
    match_keywords=["service", "down", "stopped", "not running", "unresponsive", "crashed"],
    risk_level=RiskLevel.CONFIRM,
    commands=[
        RunbookStep(description="Check service status before restart", command="systemctl status {service_name}", timeout_seconds=10),
        RunbookStep(description="Restart the service", command="systemctl restart {service_name}", timeout_seconds=30),
    ],
    verify_commands=[
        RunbookStep(description="Verify service is running after restart", command="systemctl status {service_name}", timeout_seconds=10),
    ],
    cooldown_seconds=300,
)
