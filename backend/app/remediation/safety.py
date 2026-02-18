"""
安全模块：命令校验、风险评估、限流、熔断。

最后一道防线。每条命令执行前都必须通过这里。
禁令列表硬编码 —— 不允许通过配置文件或环境变量覆盖。
"""
from __future__ import annotations

import re
import time
from collections import defaultdict

from .models import Diagnosis, RiskLevel, RunbookDefinition

# === 禁止模式 ===
FORBIDDEN_PATTERNS: list[str] = [
    # 破坏性文件系统操作
    r"rm\s+-rf\s+/(?!\S)",
    r"rm\s+-rf\s+/\*",
    r"rm\s+-rf\s+~",
    r"mkfs\.",
    r"dd\s+.*of=/dev/[sh]d",
    r">\s*/dev/[sh]d",
    # 权限提升
    r"chmod\s+.*777\s+/",
    r"chown\s+.*root\s+/",
    r"passwd\s",
    r"useradd\s",
    r"userdel\s",
    r"visudo",
    # 网络渗透
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*sh",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*bash",
    # 危险系统命令
    r"shutdown\s",
    r"reboot\b",
    r"init\s+[06]",
    r"systemctl\s+(disable|mask)\s",
    r"iptables\s+-F",
    r"iptables\s+-X",
    # 数据销毁
    r"DROP\s+DATABASE",
    r"DROP\s+TABLE",
    r"TRUNCATE\s+TABLE",
    # 挖矿
    r"xmrig",
    r"minerd",
    r"cryptonight",
]

_FORBIDDEN_RE = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]

# === 命令白名单 ===
ALLOWED_COMMAND_PREFIXES: list[str] = [
    "df", "du", "find", "ls", "cat", "head", "tail", "grep",
    "rm",
    "systemctl restart", "systemctl start", "systemctl stop", "systemctl status",
    "journalctl",
    "kill", "pkill",
    "free", "top", "ps", "vmstat", "iostat",
    "logrotate", "truncate",
    "ss", "netstat", "lsof",
    "sync", "echo",
    "apt", "yum", "dnf",
    "docker restart", "docker stop", "docker start", "docker ps", "docker logs",
    "nginx -t", "nginx -s reload",
    "sysctl",
]


def check_command_safety(cmd: str) -> tuple[bool, str]:
    """检查命令是否安全。返回 (is_safe, reason)。"""
    cmd_stripped = cmd.strip()

    if not cmd_stripped:
        return False, "Empty command"

    for pattern in _FORBIDDEN_RE:
        if pattern.search(cmd_stripped):
            return False, f"Matches forbidden pattern: {pattern.pattern}"

    cmd_lower = cmd_stripped.lower()
    allowed = any(cmd_lower.startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES)
    if not allowed:
        return False, f"Command not in allowed prefix list: {cmd_stripped.split()[0]}"

    return True, "OK"


class RateLimiter:
    """按 host+runbook 维度限流，防止无限重试。"""

    def __init__(self) -> None:
        self._history: dict[tuple[str, str], list[float]] = defaultdict(list)

    def can_execute(self, host: str, runbook_name: str, cooldown_seconds: int) -> bool:
        key = (host, runbook_name)
        now = time.time()
        self._history[key] = [t for t in self._history[key] if now - t < cooldown_seconds]
        return len(self._history[key]) == 0

    def record_execution(self, host: str, runbook_name: str) -> None:
        self._history[(host, runbook_name)].append(time.time())

    def recent_count(self, host: str, window_seconds: int = 3600) -> int:
        now = time.time()
        count = 0
        for (h, _), timestamps in self._history.items():
            if h == host:
                count += sum(1 for t in timestamps if now - t < window_seconds)
        return count


# === 熔断器 ===
MAX_FAILURES_BEFORE_CIRCUIT_BREAK = 3
CIRCUIT_BREAK_WINDOW_SECONDS = 1800


class CircuitBreaker:
    """连续失败过多时停止自动修复。"""

    def __init__(
        self,
        max_failures: int = MAX_FAILURES_BEFORE_CIRCUIT_BREAK,
        window_seconds: int = CIRCUIT_BREAK_WINDOW_SECONDS,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)

    def is_open(self, host: str) -> bool:
        now = time.time()
        self._failures[host] = [
            t for t in self._failures[host] if now - t < self.window_seconds
        ]
        return len(self._failures[host]) >= self.max_failures

    def record_failure(self, host: str) -> None:
        self._failures[host].append(time.time())

    def record_success(self, host: str) -> None:
        self._failures[host] = []


def assess_risk(
    runbook: RunbookDefinition,
    diagnosis: Diagnosis,
    recent_execution_count: int,
) -> RiskLevel:
    """综合评估风险等级。低置信度或高频执行会自动升级风险。"""
    base_risk = runbook.risk_level

    if diagnosis.confidence < 0.3:
        return RiskLevel.BLOCK

    if diagnosis.confidence < 0.7 and base_risk == RiskLevel.AUTO:
        return RiskLevel.CONFIRM

    if recent_execution_count >= 5:
        return RiskLevel.BLOCK
    if recent_execution_count >= 3 and base_risk == RiskLevel.AUTO:
        return RiskLevel.CONFIRM

    return base_risk
