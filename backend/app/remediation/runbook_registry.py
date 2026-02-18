"""
Runbook 注册表：将告警匹配到正确的 runbook。

所有 6 个 runbook 在导入时注册。简单字典，不搞插件系统。
"""
from __future__ import annotations

import logging

from .models import Diagnosis, RemediationAlert, RunbookDefinition

logger = logging.getLogger(__name__)

from .runbooks.connection_reset import RUNBOOK as CONNECTION_RESET
from .runbooks.disk_cleanup import RUNBOOK as DISK_CLEANUP
from .runbooks.log_rotation import RUNBOOK as LOG_ROTATION
from .runbooks.memory_pressure import RUNBOOK as MEMORY_PRESSURE
from .runbooks.service_restart import RUNBOOK as SERVICE_RESTART
from .runbooks.zombie_killer import RUNBOOK as ZOMBIE_KILLER


class RunbookRegistry:
    """所有可用 runbook 的注册表。"""

    def __init__(self) -> None:
        self._runbooks: dict[str, RunbookDefinition] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for runbook in [
            DISK_CLEANUP, SERVICE_RESTART, ZOMBIE_KILLER,
            MEMORY_PRESSURE, LOG_ROTATION, CONNECTION_RESET,
        ]:
            self.register(runbook)

    def register(self, runbook: RunbookDefinition) -> None:
        self._runbooks[runbook.name] = runbook
        logger.debug("Registered runbook: %s", runbook.name)

    def get(self, name: str) -> RunbookDefinition | None:
        return self._runbooks.get(name)

    def list_all(self) -> list[RunbookDefinition]:
        return list(self._runbooks.values())

    def match(self, alert: RemediationAlert, diagnosis: Diagnosis) -> RunbookDefinition | None:
        """匹配最佳 runbook：AI 建议优先 → 告警类型 → 关键词。"""
        if diagnosis.suggested_runbook:
            runbook = self._runbooks.get(diagnosis.suggested_runbook)
            if runbook:
                logger.info("Matched runbook '%s' via AI suggestion", runbook.name)
                return runbook
            logger.warning("AI suggested unknown runbook: %s", diagnosis.suggested_runbook)

        type_matches = [
            rb for rb in self._runbooks.values()
            if alert.alert_type in rb.match_alert_types
        ]
        if len(type_matches) == 1:
            logger.info("Matched runbook '%s' via alert type", type_matches[0].name)
            return type_matches[0]
        if len(type_matches) > 1:
            return self._best_keyword_match(alert, type_matches)

        all_matches = self._keyword_match_all(alert)
        if all_matches:
            logger.info("Matched runbook '%s' via keyword fallback", all_matches[0].name)
            return all_matches[0]

        logger.warning("No runbook matched for alert: %s", alert.alert_type)
        return None

    def _best_keyword_match(
        self, alert: RemediationAlert, candidates: list[RunbookDefinition]
    ) -> RunbookDefinition:
        alert_text = f"{alert.message} {alert.alert_type}".lower()

        def score(rb: RunbookDefinition) -> int:
            return sum(1 for kw in rb.match_keywords if kw.lower() in alert_text)

        return sorted(candidates, key=score, reverse=True)[0]

    def _keyword_match_all(self, alert: RemediationAlert) -> list[RunbookDefinition]:
        alert_text = f"{alert.message} {alert.alert_type}".lower()
        matches = []
        for runbook in self._runbooks.values():
            for keyword in runbook.match_keywords:
                if keyword.lower() in alert_text:
                    matches.append(runbook)
                    break
        return matches
