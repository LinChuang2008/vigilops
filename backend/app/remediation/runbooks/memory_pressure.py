"""Runbook：内存压力缓解。清理缓存、识别内存大户。"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="memory_pressure",
    description="Relieve memory pressure by clearing caches and identifying memory hogs",
    match_alert_types=["high_memory", "oom_warning", "memory_usage_high", "swap_usage_high"],
    match_keywords=["memory", "OOM", "out of memory", "swap", "ram"],
    risk_level=RiskLevel.CONFIRM,
    commands=[
        RunbookStep(description="Show current memory usage", command="free -h", timeout_seconds=10),
        RunbookStep(description="List top memory consumers", command="ps aux --sort=-%mem | head -10", timeout_seconds=10),
        RunbookStep(description="Sync filesystem buffers", command="sync", timeout_seconds=15),
        RunbookStep(description="Drop page cache (safe, recoverable)", command="echo 3 > /proc/sys/vm/drop_caches", timeout_seconds=10),
    ],
    verify_commands=[
        RunbookStep(description="Check memory after cleanup", command="free -h", timeout_seconds=10),
    ],
    cooldown_seconds=600,
)
