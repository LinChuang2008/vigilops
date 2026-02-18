"""Runbook：磁盘清理。清理临时文件、旧日志、包缓存。"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="disk_cleanup",
    description="Clean up disk space by removing temp files, old logs, and package caches",
    match_alert_types=["disk_full", "disk_space_low", "disk_usage_high"],
    match_keywords=["disk", "space", "full", "no space left", "inode"],
    risk_level=RiskLevel.AUTO,
    commands=[
        RunbookStep(description="Remove temp files older than 7 days", command="find /tmp -type f -mtime +7 -delete", timeout_seconds=60),
        RunbookStep(description="Clean old journal logs (keep last 3 days)", command="journalctl --vacuum-time=3d", timeout_seconds=30),
        RunbookStep(description="Remove old rotated logs", command="find /var/log -name '*.gz' -mtime +7 -delete", timeout_seconds=60),
        RunbookStep(description="Clean package manager cache", command="apt clean", timeout_seconds=60),
    ],
    verify_commands=[
        RunbookStep(description="Check disk usage after cleanup", command="df -h /", timeout_seconds=10),
    ],
    cooldown_seconds=600,
)
