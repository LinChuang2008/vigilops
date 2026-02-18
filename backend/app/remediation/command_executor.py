"""
命令执行器，支持 dry-run 模式。

默认 dry_run=True，只记录不执行。生产环境通过配置开启真实执行。
"""
from __future__ import annotations

import asyncio
import logging
import time

from .models import CommandResult, RunbookStep
from .safety import check_command_safety

logger = logging.getLogger(__name__)


class CommandExecutor:
    """执行修复命令，带安全检查和 dry-run 支持。"""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self._execution_log: list[CommandResult] = []

    @property
    def execution_log(self) -> list[CommandResult]:
        return list(self._execution_log)

    async def execute_step(self, step: RunbookStep) -> CommandResult:
        """执行单条 runbook 步骤。"""
        is_safe, reason = check_command_safety(step.command)
        if not is_safe:
            result = CommandResult(
                command=step.command,
                exit_code=-1,
                stderr=f"BLOCKED by safety check: {reason}",
                executed=False,
            )
            self._execution_log.append(result)
            logger.warning("Command blocked: %s -- %s", step.command, reason)
            return result

        if self.dry_run:
            result = CommandResult(
                command=step.command,
                exit_code=0,
                stdout=f"[DRY RUN] Would execute: {step.command}",
                executed=False,
                duration_ms=0,
            )
            self._execution_log.append(result)
            logger.info("[DRY RUN] %s: %s", step.description, step.command)
            return result

        return await self._execute_real(step)

    async def execute_steps(self, steps: list[RunbookStep]) -> list[CommandResult]:
        """顺序执行多条步骤，遇到失败立即停止。"""
        results: list[CommandResult] = []
        for step in steps:
            result = await self.execute_step(step)
            results.append(result)
            if result.exit_code != 0:
                logger.warning(
                    "Step failed (exit=%d), stopping: %s",
                    result.exit_code,
                    step.command,
                )
                break
        return results

    async def _execute_real(self, step: RunbookStep) -> CommandResult:
        """通过 subprocess 真实执行命令。"""
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                step.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=step.timeout_seconds
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                elapsed = int((time.monotonic() - start) * 1000)
                result = CommandResult(
                    command=step.command,
                    exit_code=-1,
                    stderr=f"Command timed out after {step.timeout_seconds}s",
                    executed=True,
                    duration_ms=elapsed,
                )
                self._execution_log.append(result)
                return result

            elapsed = int((time.monotonic() - start) * 1000)
            result = CommandResult(
                command=step.command,
                exit_code=proc.returncode or 0,
                stdout=stdout_bytes.decode(errors="replace")[:4096],
                stderr=stderr_bytes.decode(errors="replace")[:4096],
                executed=True,
                duration_ms=elapsed,
            )
            self._execution_log.append(result)
            return result

        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            result = CommandResult(
                command=step.command,
                exit_code=-1,
                stderr=str(e),
                executed=True,
                duration_ms=elapsed,
            )
            self._execution_log.append(result)
            return result
