"""Runbook：日志轮转。强制轮转和截断超大日志文件。"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="log_rotation",
    description="Force log rotation and truncate oversized log files",
    match_alert_types=["log_file_too_large", "disk_full", "log_growth"],
    match_keywords=["log", "rotation", "large file", "growing fast"],
    risk_level=RiskLevel.AUTO,
    commands=[
        RunbookStep(description="Find large log files", command="find /var/log -type f -size +100M -exec ls -lh {} +", timeout_seconds=30),
        RunbookStep(description="Force logrotate on all configs", command="logrotate -f /etc/logrotate.conf", timeout_seconds=60),
    ],
    verify_commands=[
        RunbookStep(description="Check log directory size after rotation", command="du -sh /var/log", timeout_seconds=10),
    ],
    cooldown_seconds=600,
)
