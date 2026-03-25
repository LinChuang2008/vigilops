"""Runbook 注册中心。"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_runbook import CustomRunbook
from .models import Diagnosis, RemediationAlert, RiskLevel, RunbookDefinition, RunbookStep

logger = logging.getLogger(__name__)


class RunbookRegistry:
    """只维护用户自定义 runbook 的内存索引。"""

    def __init__(self) -> None:
        self._runbooks: dict[str, RunbookDefinition] = {}

    async def load_from_db(self, db: AsyncSession) -> None:
        """从数据库加载当前启用的自定义 runbook。"""
        result = await db.execute(
            select(CustomRunbook)
            .where(CustomRunbook.is_active == True)  # noqa: E712
            .order_by(CustomRunbook.created_at.asc())
        )
        self._runbooks.clear()
        for runbook in result.scalars().all():
            self.register_custom(runbook)

    def register(self, runbook: RunbookDefinition) -> None:
        self._runbooks[runbook.name] = runbook
        logger.debug("Registered runbook: %s", runbook.name)

    def get(self, name: str) -> RunbookDefinition | None:
        return self._runbooks.get(name)

    def list_all(self) -> list[RunbookDefinition]:
        return list(self._runbooks.values())

    def match(self, alert: RemediationAlert, diagnosis: Diagnosis) -> RunbookDefinition | None:
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

    def register_custom(self, custom_runbook: "CustomRunbook") -> None:
        risk_map = {
            "auto": RiskLevel.AUTO,
            "confirm": RiskLevel.CONFIRM,
            "manual": RiskLevel.CONFIRM,
            "block": RiskLevel.BLOCK,
        }
        steps = []
        for step in (custom_runbook.steps or []):
            steps.append(RunbookStep(
                description=step.get("name", ""),
                command=step.get("command", ""),
                timeout_seconds=step.get("timeout_sec", 30),
            ))

        definition = RunbookDefinition(
            name=custom_runbook.name,
            description=custom_runbook.description or "",
            match_alert_types=[],
            match_keywords=custom_runbook.trigger_keywords or [],
            risk_level=risk_map.get(custom_runbook.risk_level, RiskLevel.CONFIRM),
            commands=steps,
            verify_commands=[],
            cooldown_seconds=300,
        )
        self.register(definition)
        logger.info("Registered custom runbook: %s (id=%s)", custom_runbook.name, custom_runbook.id)
