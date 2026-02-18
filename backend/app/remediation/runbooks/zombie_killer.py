"""Runbook：僵尸进程清理。清理 defunct 进程。"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="zombie_killer",
    description="Kill zombie/defunct processes and their parent processes",
    match_alert_types=["zombie_processes", "defunct_processes", "high_process_count"],
    match_keywords=["zombie", "defunct", "Z state", "too many processes"],
    risk_level=RiskLevel.AUTO,
    commands=[
        RunbookStep(description="List zombie processes", command="ps aux | grep -w Z | grep -v grep", timeout_seconds=10),
        RunbookStep(description="Kill parent processes of zombies to reap them", command="ps -eo ppid,stat | grep Z | awk '{print $1}' | sort -u | head -20", timeout_seconds=10),
    ],
    verify_commands=[
        RunbookStep(description="Check remaining zombie count", command="ps aux | grep -w Z | grep -v grep", timeout_seconds=10),
    ],
    cooldown_seconds=300,
)
